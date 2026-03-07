"""
Verify MongoDB connection and display collection stats for the AI brain database.
"""
import os
import sys
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("MONGODB_DB", "ai_brain")

EXPECTED_COLLECTIONS = [
    "prompt_templates",
    "session_memory",
    "intent_registry",
    "model_config",
    "context_chains",
]


def main():
    print(f"Connecting to: {MONGODB_URI[:40]}...")
    try:
        client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        client.admin.command("ping")
    except (ConnectionFailure, OperationFailure) as e:
        print(f"Connection failed: {e}")
        sys.exit(1)

    print("Connection OK\n")
    db = client[DB_NAME]
    existing = db.list_collection_names()

    print(f"Database: {DB_NAME}")
    print(f"{'Collection':<30} {'Documents':>10}  Status")
    print("-" * 55)

    for name in EXPECTED_COLLECTIONS:
        count = db[name].count_documents({}) if name in existing else 0
        status = "OK" if name in existing else "MISSING — run seed_collections.py"
        print(f"  {name:<28} {count:>10}  {status}")

    extra = [c for c in existing if c not in EXPECTED_COLLECTIONS]
    if extra:
        print(f"\nAdditional collections: {', '.join(extra)}")

    client.close()


if __name__ == "__main__":
    main()
