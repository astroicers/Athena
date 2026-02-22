#!/usr/bin/env python3
"""RAG Stats — 顯示知識庫統計"""
import sys

def stats(index_path: str = ".rag/index"):
    try:
        import chromadb
    except ImportError:
        print("❌ 請執行：pip install chromadb sentence-transformers")
        sys.exit(1)

    try:
        client = chromadb.PersistentClient(path=index_path)
        collection = client.get_collection("asp_knowledge")
    except Exception:
        print("⚠️  RAG 索引不存在，請先執行：make rag-index")
        sys.exit(1)

    count = collection.count()
    peek = collection.peek(limit=5)
    sources = list({m["source"] for m in peek["metadatas"]})

    print(f"\n📊 RAG 知識庫統計")
    print(f"{'─'*40}")
    print(f"文件片段總數：{count}")
    print(f"索引路徑：{index_path}")
    print(f"\n範例來源（前 5 筆）：")
    for s in sources:
        print(f"  - {s}")
    print()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", default=".rag/index")
    args = parser.parse_args()
    stats(args.index)
