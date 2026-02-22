#!/usr/bin/env python3
"""
RAG Index Builder
建立本地向量知識庫，將 docs/ 與 profiles/ 的文件向量化後存入 ChromaDB
"""
import argparse
import glob
import os
import sys

def build_index(sources: list[str], output: str, model: str):
    try:
        import chromadb
        from sentence_transformers import SentenceTransformer
    except ImportError:
        print("❌ 缺少依賴，請執行：pip install chromadb sentence-transformers")
        sys.exit(1)

    print(f"🔍 載入嵌入模型：{model}")
    embedder = SentenceTransformer(model)

    client = chromadb.PersistentClient(path=output)
    
    # 重建集合
    try:
        client.delete_collection("asp_knowledge")
    except Exception:
        pass
    collection = client.create_collection("asp_knowledge")

    docs, metas, ids = [], [], []
    doc_count = 0

    for source_dir in sources:
        for filepath in glob.glob(f"{source_dir}/**/*.md", recursive=True):
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read().strip()
            if not content:
                continue
            
            # 分塊：每 500 字一塊，overlap 100 字
            chunks = chunk_text(content, chunk_size=500, overlap=100)
            for i, chunk in enumerate(chunks):
                doc_id = f"{filepath}::{i}"
                docs.append(chunk)
                metas.append({"source": filepath, "chunk": i})
                ids.append(doc_id)
                doc_count += 1

    if not docs:
        print("⚠️  未找到任何文件")
        return

    print(f"📚 向量化 {doc_count} 個文件片段...")
    
    # 批次處理避免 OOM
    batch_size = 100
    for i in range(0, len(docs), batch_size):
        batch_docs = docs[i:i+batch_size]
        batch_metas = metas[i:i+batch_size]
        batch_ids = ids[i:i+batch_size]
        embeddings = embedder.encode(batch_docs).tolist()
        collection.add(
            documents=batch_docs,
            embeddings=embeddings,
            metadatas=batch_metas,
            ids=batch_ids,
        )
        print(f"  進度：{min(i+batch_size, len(docs))}/{len(docs)}", end="\r")

    print(f"\n✅ RAG 索引完成：{doc_count} 個片段，儲存於 {output}")


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 100) -> list[str]:
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunks.append(" ".join(words[start:end]))
        start += chunk_size - overlap
    return chunks


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", action="append", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--model", default="all-MiniLM-L6-v2")
    args = parser.parse_args()
    build_index(args.source, args.output, args.model)
