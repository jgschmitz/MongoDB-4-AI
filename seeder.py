"""
Seed MongoDB collections with starter documents for the AI intelligence layer.
"""
import os
from datetime import datetime, timezone
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("MONGODB_DB", "ai_brain")


def seed_prompt_templates(db):
    col = db["prompt_templates"]
    col.drop()
    col.insert_many([
        {
            "_id": "tmpl_summarize_v3",
            "name": "summarize_document",
            "version": 3,
            "created_at": datetime.now(timezone.utc),
            "variants": {
                "openai-gpt-4o": {
                    "system": "You are a concise document analyst.",
                    "user_template": "Summarize the following in {{max_sentences}} sentences:\n\n{{document}}"
                },
                "anthropic-claude-3-5": {
                    "system": "Analyze and compress the following text.",
                    "user_template": "<document>{{document}}</document>\nReturn a {{max_sentences}}-sentence summary."
                },
                "llama-3-70b": {
                    "prompt_template": "[INST] Summarize this in {{max_sentences}} sentences: {{document}} [/INST]"
                }
            },
            "tags": ["summarization", "rag", "production"]
        },
        {
            "_id": "tmpl_contract_review_v2",
            "name": "contract_review",
            "version": 2,
            "created_at": datetime.now(timezone.utc),
            "variants": {
                "openai-gpt-4o": {
                    "system": "You are a legal document analyst. Identify risks, obligations, and key clauses.",
                    "user_template": "Review the following contract excerpt and highlight key risks:\n\n{{document}}"
                },
                "anthropic-claude-3-5": {
                    "system": "You are a precise legal analyst.",
                    "user_template": "<contract>{{document}}</contract>\nIdentify key risks and obligations."
                }
            },
            "tags": ["legal", "contract", "rag"]
        }
    ])
    print(f"  Seeded {col.count_documents({})} prompt templates")


def seed_intent_registry(db):
    col = db["intent_registry"]
    col.drop()
    col.insert_many([
        {
            "_id": "intent_contract_review",
            "label": "contract_review",
            "description": "User wants to review, redline, or summarize a contract",
            "confidence_threshold": 0.82,
            "routing": {
                "primary_model": "anthropic-claude-3-5",
                "fallback_model": "openai-gpt-4o",
                "prompt_template_id": "tmpl_contract_review_v2",
                "tools_enabled": ["vector_search", "pdf_parser", "citation_extractor"]
            },
            "rag_config": {
                "collection": "contract_embeddings",
                "top_k": 8,
                "similarity_metric": "cosine",
                "min_score": 0.75
            },
            "guardrails": {
                "pii_redaction": True,
                "max_output_tokens": 4096,
                "content_filter": "legal_safe"
            }
        },
        {
            "_id": "intent_summarize",
            "label": "summarize_document",
            "description": "User wants a document or text summarized",
            "confidence_threshold": 0.78,
            "routing": {
                "primary_model": "openai-gpt-4o",
                "fallback_model": "anthropic-claude-3-5",
                "prompt_template_id": "tmpl_summarize_v3",
                "tools_enabled": ["vector_search"]
            },
            "rag_config": {
                "collection": "document_embeddings",
                "top_k": 5,
                "similarity_metric": "cosine",
                "min_score": 0.70
            },
            "guardrails": {
                "pii_redaction": False,
                "max_output_tokens": 2048,
                "content_filter": "standard"
            }
        }
    ])
    print(f"  Seeded {col.count_documents({})} intents")


def seed_model_config(db):
    col = db["model_config"]
    col.drop()
    col.insert_one({
        "_id": "cfg_production_active",
        "active": True,
        "effective_date": datetime.now(timezone.utc),
        "primary": {
            "provider": "openai",
            "model": "gpt-4o",
            "api_version": "2025-12-01",
            "temperature": 0.3,
            "max_tokens": 8192,
            "timeout_ms": 15000
        },
        "fallback": {
            "provider": "anthropic",
            "model": "claude-3-5-sonnet-20241022",
            "temperature": 0.3,
            "max_tokens": 8192,
            "timeout_ms": 20000
        },
        "cost_controls": {
            "monthly_budget_usd": 5000,
            "per_request_cap_usd": 0.50,
            "alert_threshold_pct": 80
        }
    })
    print(f"  Seeded {col.count_documents({})} model config")


def main():
    client = MongoClient(MONGODB_URI)
    db = client[DB_NAME]
    print(f"Seeding database: {DB_NAME}")
    seed_prompt_templates(db)
    seed_intent_registry(db)
    seed_model_config(db)
    print("Done.")
    client.close()


if __name__ == "__main__":
    main()
