"""
Update the active model config in MongoDB without touching application code.
Usage:
    python swap_model.py --provider openai --model gpt-4o --temperature 0.3
    python swap_model.py --provider anthropic --model claude-3-5-sonnet-20241022
"""
import os
import argparse
from datetime import datetime, timezone
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("MONGODB_DB", "ai_brain")

SUPPORTED_PROVIDERS = {
    "openai": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"],
    "anthropic": ["claude-3-5-sonnet-20241022", "claude-3-opus-20240229", "claude-3-haiku-20240307"],
    "ollama": ["llama-3-70b", "llama-3-8b", "mistral-7b"],
}


def main():
    parser = argparse.ArgumentParser(description="Swap the active LLM in model_config")
    parser.add_argument("--provider", required=True, choices=SUPPORTED_PROVIDERS.keys())
    parser.add_argument("--model", required=True)
    parser.add_argument("--temperature", type=float, default=0.3)
    parser.add_argument("--max-tokens", type=int, default=8192)
    parser.add_argument("--slot", choices=["primary", "fallback"], default="primary",
                        help="Which slot to update (default: primary)")
    args = parser.parse_args()

    client = MongoClient(MONGODB_URI)
    db = client[DB_NAME]
    col = db["model_config"]

    current = col.find_one({"active": True})
    if not current:
        print("No active model_config found. Run seed_collections.py first.")
        return

    old = current[args.slot]
    update = {
        f"{args.slot}.provider": args.provider,
        f"{args.slot}.model": args.model,
        f"{args.slot}.temperature": args.temperature,
        f"{args.slot}.max_tokens": args.max_tokens,
        f"{args.slot}.swapped_at": datetime.now(timezone.utc),
    }

    col.update_one({"active": True}, {"$set": update})

    print(f"Model swap complete ({args.slot}):")
    print(f"  Before : {old['provider']} / {old['model']}")
    print(f"  After  : {args.provider} / {args.model}")
    client.close()


if __name__ == "__main__":
    main()
