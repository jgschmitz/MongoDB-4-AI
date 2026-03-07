"""
MongoDB 4 AI — Intelligence Layer Orchestrator
Resolves intent, loads prompt template, hydrates session memory, calls the active LLM.

Usage:
    python app.py --user usr_001 --query "Summarize the key risks in our Q4 report"
    python app.py --user usr_001 --session sess_abc123 --query "What did we discuss earlier?"
"""
import os
import argparse
import uuid
from datetime import datetime, timezone

from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
if not MONGODB_URI:
    raise EnvironmentError("MONGODB_URI is not set. Copy .env.example to .env and fill in your Atlas connection string.")

DB_NAME = os.getenv("MONGODB_DB", "ai_brain")


# ---------------------------------------------------------------------------
# MongoDB helpers
# ---------------------------------------------------------------------------

def get_db():
    client = MongoClient(MONGODB_URI)
    return client[DB_NAME], client


def load_model_config(db) -> dict:
    cfg = db["model_config"].find_one({"active": True})
    if not cfg:
        raise RuntimeError("No active model_config found. Run: python scripts/seed_collections.py")
    return cfg


def resolve_intent(db, query: str) -> dict:
    """
    Naive keyword-based intent resolution.
    Replace with an embedding classifier or LLM-based router in production.
    """
    query_lower = query.lower()
    intents = list(db["intent_registry"].find({}))
    for intent in intents:
        if any(kw in query_lower for kw in intent["label"].split("_")):
            return intent
    return intents[0] if intents else {}


def load_prompt_template(db, template_id: str, model_key: str) -> str:
    tmpl = db["prompt_templates"].find_one({"_id": template_id})
    if not tmpl:
        raise RuntimeError(f"Prompt template not found: {template_id}")
    variants = tmpl.get("variants", {})
    variant = variants.get(model_key) or next(iter(variants.values()))
    return variant.get("user_template") or variant.get("prompt_template", "")


def load_or_create_session(db, session_id: str | None, user_id: str, model: str) -> dict:
    col = db["session_memory"]
    if session_id:
        session = col.find_one({"_id": session_id})
        if session:
            return session
    new_session = {
        "_id": f"sess_{uuid.uuid4().hex[:8]}",
        "user_id": user_id,
        "model": model,
        "created_at": datetime.now(timezone.utc),
        "last_active": datetime.now(timezone.utc),
        "context_window_tokens": 0,
        "turns": [],
        "metadata": {}
    }
    col.insert_one(new_session)
    return new_session


def append_turn(db, session_id: str, role: str, content: str, tokens: int = 0):
    col = db["session_memory"]
    session = col.find_one({"_id": session_id})
    turn_number = len(session.get("turns", [])) + 1
    col.update_one(
        {"_id": session_id},
        {
            "$push": {"turns": {
                "turn": turn_number,
                "role": role,
                "content": content,
                "timestamp": datetime.now(timezone.utc),
                "tokens_used": tokens
            }},
            "$set": {"last_active": datetime.now(timezone.utc)},
            "$inc": {"context_window_tokens": tokens}
        }
    )


def build_context_from_memory(session: dict) -> str:
    turns = session.get("turns", [])
    if not turns:
        return ""
    lines = []
    for t in turns[-6:]:  # last 3 exchanges
        lines.append(f"{t['role'].upper()}: {t['content']}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# LLM dispatch
# ---------------------------------------------------------------------------

def call_openai(prompt: str, config: dict) -> tuple[str, int]:
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model=config["model"],
        temperature=config.get("temperature", 0.3),
        max_tokens=config.get("max_tokens", 2048),
        messages=[{"role": "user", "content": prompt}]
    )
    content = response.choices[0].message.content
    tokens = response.usage.total_tokens
    return content, tokens


def call_anthropic(prompt: str, config: dict) -> tuple[str, int]:
    import anthropic
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    response = client.messages.create(
        model=config["model"],
        max_tokens=config.get("max_tokens", 2048),
        messages=[{"role": "user", "content": prompt}]
    )
    content = response.content[0].text
    tokens = response.usage.input_tokens + response.usage.output_tokens
    return content, tokens


def call_llm(prompt: str, model_cfg: dict) -> tuple[str, int]:
    primary = model_cfg["primary"]
    provider = primary["provider"]
    try:
        if provider == "openai":
            return call_openai(prompt, primary)
        elif provider == "anthropic":
            return call_anthropic(prompt, primary)
        else:
            raise ValueError(f"Unsupported provider: {provider}")
    except Exception as e:
        print(f"Primary model failed ({e}), trying fallback...")
        fallback = model_cfg.get("fallback", {})
        if fallback.get("provider") == "openai":
            return call_openai(prompt, fallback)
        elif fallback.get("provider") == "anthropic":
            return call_anthropic(prompt, fallback)
        raise


# ---------------------------------------------------------------------------
# Main orchestration loop
# ---------------------------------------------------------------------------

def run(user_id: str, query: str, session_id: str | None = None):
    db, client = get_db()

    model_cfg = load_model_config(db)
    primary = model_cfg["primary"]
    model_key = f"{primary['provider']}-{primary['model'].split('-')[0]}"

    intent = resolve_intent(db, query)
    template_id = intent.get("routing", {}).get("prompt_template_id", "")

    session = load_or_create_session(db, session_id, user_id, primary["model"])
    session_id = session["_id"]
    print(f"Session  : {session_id}")
    print(f"Intent   : {intent.get('label', 'unknown')}")
    print(f"Model    : {primary['provider']} / {primary['model']}\n")

    context = build_context_from_memory(session)
    try:
        template = load_prompt_template(db, template_id, model_key)
        prompt = template.replace("{{document}}", query).replace("{{max_sentences}}", "5")
    except Exception:
        prompt = query

    if context:
        prompt = f"Previous conversation:\n{context}\n\n{prompt}"

    append_turn(db, session_id, "user", query)

    response, tokens = call_llm(prompt, model_cfg)

    append_turn(db, session_id, "assistant", response, tokens)

    print(f"Response ({tokens} tokens):\n")
    print(response)

    client.close()
    return response


def main():
    parser = argparse.ArgumentParser(description="MongoDB AI Intelligence Layer")
    parser.add_argument("--user", required=True, help="User ID")
    parser.add_argument("--query", required=True, help="Natural language query")
    parser.add_argument("--session", help="Existing session ID to continue")
    args = parser.parse_args()

    run(user_id=args.user, query=args.query, session_id=args.session)


if __name__ == "__main__":
    main()
