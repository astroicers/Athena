#!/usr/bin/env python3
"""
RAG Index Builder
建立本地向量知識庫，將 docs/ 與 profiles/ 的文件向量化後存入 ChromaDB

支援增量模式（--incremental）：只重建有變更的檔案，跳過未修改的檔案。
"""
import argparse
import glob
import hashlib
import json
import os
import sys


MANIFEST_FILENAME = "index_manifest.json"


def file_hash(filepath: str) -> str:
    with open(filepath, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def load_manifest(output: str) -> dict:
    manifest_path = os.path.join(output, MANIFEST_FILENAME)
    if os.path.exists(manifest_path):
        with open(manifest_path, "r") as f:
            return json.load(f)
    return {}


def save_manifest(output: str, manifest: dict):
    os.makedirs(output, exist_ok=True)
    manifest_path = os.path.join(output, MANIFEST_FILENAME)
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)


def collect_files(sources: list[str]) -> dict[str, str]:
    """Return {filepath: sha256_hash} for all .md files in sources."""
    files = {}
    for source_dir in sources:
        for filepath in glob.glob(f"{source_dir}/**/*.md", recursive=True):
            files[filepath] = file_hash(filepath)
    return files


def detect_adr_status(filepath: str) -> str | None:
    """Extract ADR status from file content for metadata."""
    if "/adr/" not in filepath.lower() and "ADR-" not in os.path.basename(filepath):
        return None
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                if "狀態" in line and "`" in line:
                    start = line.index("`") + 1
                    end = line.index("`", start)
                    return line[start:end]
    except (ValueError, OSError):
        pass
    return None


def build_index(sources: list[str], output: str, model: str, incremental: bool = False):
    try:
        import chromadb
        from sentence_transformers import SentenceTransformer
    except ImportError:
        print("❌ 缺少依賴，請執行：pip install chromadb sentence-transformers")
        sys.exit(1)

    current_files = collect_files(sources)
    old_manifest = load_manifest(output) if incremental else {}

    # Determine which files need (re-)indexing
    if incremental and old_manifest:
        changed = {fp for fp, h in current_files.items() if old_manifest.get(fp) != h}
        removed = set(old_manifest.keys()) - set(current_files.keys())
        if not changed and not removed:
            print("✅ 索引已是最新，無需更新")
            return
        print(f"📝 增量更新：{len(changed)} 個變更、{len(removed)} 個刪除")
    else:
        changed = set(current_files.keys())
        removed = set()

    print(f"🔍 載入嵌入模型：{model}")
    embedder = SentenceTransformer(model)

    client = chromadb.PersistentClient(path=output)

    if not incremental:
        try:
            client.delete_collection("asp_knowledge")
        except Exception:
            pass
        collection = client.create_collection("asp_knowledge")
    else:
        collection = client.get_or_create_collection("asp_knowledge")
        # Remove chunks from changed/removed files
        for fp in changed | removed:
            existing = collection.get(where={"source": fp})
            if existing["ids"]:
                collection.delete(ids=existing["ids"])

    docs, metas, ids = [], [], []
    doc_count = 0

    for filepath in changed:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read().strip()
        if not content:
            continue

        adr_status = detect_adr_status(filepath)
        chunks = chunk_text(content, chunk_size=500, overlap=100)
        for i, chunk in enumerate(chunks):
            doc_id = f"{filepath}::{i}"
            meta = {"source": filepath, "chunk": i}
            if adr_status:
                meta["adr_status"] = adr_status
            docs.append(chunk)
            metas.append(meta)
            ids.append(doc_id)
            doc_count += 1

    if docs:
        print(f"📚 向量化 {doc_count} 個文件片段...")
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
        print()

    # Save updated manifest
    save_manifest(output, current_files)

    mode_label = "增量" if incremental else "全量"
    print(f"✅ RAG 索引完成（{mode_label}）：{doc_count} 個片段，儲存於 {output}")


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
    parser.add_argument("--incremental", action="store_true",
                        help="只更新有變更的檔案，跳過未修改的")
    args = parser.parse_args()
    build_index(args.source, args.output, args.model, args.incremental)
