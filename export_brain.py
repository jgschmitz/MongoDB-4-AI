"""
Export the AI intelligence layer collections to JSON for backup, migration, or inspection.
Usage:
    python export_brain.py
    python export_brain.py --output-dir ./exports --pretty
"""
import os
import json
import argparse
from datetime import datetime, timezone
from dotenv import load_dotenv
from pymongo import MongoClient
from bson import json_util

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("MONGODB_DB", "ai_brain")

COLLECTIONS = [
    "prompt_templates",
    "intent_registry",
    "model_config",
    "context_chains",
]


def export_collection(db, name: str, output_dir: str, pretty: bool):
    docs = list(db[name].find({}))
    filename = os.path.join(output_dir, f"{name}.json")
    indent = 2 if pretty else None
    with open(filename, "w") as f:
        f.write(json_util.dumps(docs, indent=indent))
    print(f"  Exported {len(docs):>4} documents -> {filename}")


def main():
    parser = argparse.ArgumentParser(description="Export AI brain collections to JSON")
    parser.add_argument("--output-dir", default="./exports")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    client = MongoClient(MONGODB_URI)
    db = client[DB_NAME]

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    print(f"Exporting database '{DB_NAME}' at {ts}\n")

    for name in COLLECTIONS:
        export_collection(db, name, args.output_dir, args.pretty)

    print(f"\nExport complete -> {args.output_dir}/")
    client.close()


if __name__ == "__main__":
    main()
