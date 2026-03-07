"""
Run a vector similarity search against a MongoDB Atlas collection.
Requires Atlas Vector Search index named 'vector_index' on the target collection.

Usage:
    python vector_search.py --query "contract termination clauses" --collection contract_embeddings
    python vector_search.py --query "Q4 revenue risks" --collection document_embeddings --top-k 10
"""
import os
import argparse
from dotenv import load_dotenv
from pymongo import MongoClient
from sentence_transformers import SentenceTransformer

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("MONGODB_DB", "ai_brain")
EMBED_MODEL = os.getenv("EMBED_MODEL", "all-MiniLM-L6-v2")


def embed(text: str, model: SentenceTransformer) -> list[float]:
    return model.encode(text, normalize_embeddings=True).tolist()


def vector_search(col, query_embedding: list[float], top_k: int = 5) -> list[dict]:
    pipeline = [
        {
            "$vectorSearch": {
                "index": "vector_index",
                "path": "embedding",
                "queryVector": query_embedding,
                "numCandidates": top_k * 10,
                "limit": top_k
            }
        },
        {
            "$project": {
                "_id": 1,
                "text": 1,
                "source": 1,
                "score": {"$meta": "vectorSearchScore"}
            }
        }
    ]
    return list(col.aggregate(pipeline))


def main():
    parser = argparse.ArgumentParser(description="Run Atlas Vector Search")
    parser.add_argument("--query", required=True, help="Natural language query")
    parser.add_argument("--collection", required=True, help="Target embeddings collection")
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    print(f"Loading embedding model: {EMBED_MODEL}")
    model = SentenceTransformer(EMBED_MODEL)

    print(f"Embedding query: \"{args.query}\"")
    query_vec = embed(args.query, model)

    client = MongoClient(MONGODB_URI)
    col = client[DB_NAME][args.collection]

    results = vector_search(col, query_vec, top_k=args.top_k)

    if not results:
        print("No results returned. Verify the vector_index exists on this collection.")
        return

    print(f"\nTop {len(results)} results from '{args.collection}':\n")
    for i, r in enumerate(results, 1):
        score = r.get("score", 0)
        text = r.get("text", "")[:200]
        source = r.get("source", "unknown")
        print(f"  [{i}] score={score:.4f}  source={source}")
        print(f"      {text}{'...' if len(r.get('text','')) > 200 else ''}\n")

    client.close()


if __name__ == "__main__":
    main()
