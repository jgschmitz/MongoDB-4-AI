"""
Inspect and manage session memory documents.
Usage:
    python session_inspector.py --list
    python session_inspector.py --session sess_a1b2c3d4
    python session_inspector.py --session sess_a1b2c3d4 --clear
    python session_inspector.py --prune-days 30
"""
import os
import argparse
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from pymongo import MongoClient, DESCENDING

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("MONGODB_DB", "ai_brain")


def list_sessions(col, limit=20):
    sessions = col.find({}, {
        "_id": 1, "user_id": 1, "model": 1, "last_active": 1, "turns": 1
    }).sort("last_active", DESCENDING).limit(limit)

    print(f"{'Session ID':<20} {'User':<12} {'Model':<25} {'Turns':>6}  Last Active")
    print("-" * 85)
    for s in sessions:
        turns = len(s.get("turns", []))
        last = s.get("last_active", "—")
        if isinstance(last, datetime):
            last = last.strftime("%Y-%m-%d %H:%M")
        print(f"  {s['_id']:<18} {s.get('user_id','—'):<12} {s.get('model','—'):<25} {turns:>6}  {last}")


def show_session(col, session_id):
    s = col.find_one({"_id": session_id})
    if not s:
        print(f"Session not found: {session_id}")
        return

    print(f"Session : {s['_id']}")
    print(f"User    : {s.get('user_id')}")
    print(f"Model   : {s.get('model')}")
    print(f"Tokens  : {s.get('context_window_tokens')}")
    print(f"Created : {s.get('created_at')}")
    print(f"Active  : {s.get('last_active')}")
    print(f"Meta    : {s.get('metadata', {})}")
    print(f"\nTurns ({len(s.get('turns', []))}):")
    for t in s.get("turns", []):
        role = t["role"].upper()
        print(f"\n  [{t['turn']}] {role}")
        print(f"  {t['content']}")


def clear_session(col, session_id):
    result = col.update_one(
        {"_id": session_id},
        {"$set": {"turns": [], "context_window_tokens": 0}}
    )
    if result.matched_count:
        print(f"Cleared turns for session: {session_id}")
    else:
        print(f"Session not found: {session_id}")


def prune_sessions(col, days):
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    result = col.delete_many({"last_active": {"$lt": cutoff}})
    print(f"Pruned {result.deleted_count} sessions inactive for more than {days} days")


def main():
    parser = argparse.ArgumentParser(description="Inspect and manage session memory")
    parser.add_argument("--list", action="store_true", help="List recent sessions")
    parser.add_argument("--session", help="Show a specific session by ID")
    parser.add_argument("--clear", action="store_true", help="Clear turns for --session")
    parser.add_argument("--prune-days", type=int, help="Delete sessions inactive for N days")
    args = parser.parse_args()

    client = MongoClient(MONGODB_URI)
    col = client[DB_NAME]["session_memory"]

    if args.list:
        list_sessions(col)
    elif args.session and args.clear:
        clear_session(col, args.session)
    elif args.session:
        show_session(col, args.session)
    elif args.prune_days:
        prune_sessions(col, args.prune_days)
    else:
        parser.print_help()

    client.close()


if __name__ == "__main__":
    main()
