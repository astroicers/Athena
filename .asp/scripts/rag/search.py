#!/usr/bin/env python3
"""
RAG Search
查詢本地向量知識庫，召回相關文件片段
"""
import argparse
import sys

def search(query: str, top_k: int = 3, index_path: str = ".rag/index", model: str = "all-MiniLM-L6-v2"):
    try:
        import chromadb
        from sentence_transformers import SentenceTransformer
    except ImportError:
        print("❌ 缺少依賴，請執行：pip install chromadb sentence-transformers")
        sys.exit(1)

    try:
        client = chromadb.PersistentClient(path=index_path)
        collection = client.get_collection("asp_knowledge")
    except Exception:
        print("⚠️  RAG 索引不存在，請先執行：make rag-index")
        sys.exit(1)

    embedder = SentenceTransformer(model)
    query_embedding = embedder.encode([query]).tolist()

    results = collection.query(
        query_embeddings=query_embedding,
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    print(f"\n🔍 查詢：{query}")
    print(f"📚 召回 {len(results['documents'][0])} 個相關片段\n")

    for i, (doc, meta, dist) in enumerate(zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    )):
        similarity = round(1 - dist, 3)
        print(f"{'─'*60}")
        print(f"[{i+1}] 來源：{meta['source']}（相似度 {similarity}）")
        print(f"{doc[:400]}{'...' if len(doc) > 400 else ''}")
        print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", required=True)
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--index", default=".rag/index")
    parser.add_argument("--model", default="all-MiniLM-L6-v2")
    args = parser.parse_args()
    search(args.query, args.top_k, args.index, args.model)
