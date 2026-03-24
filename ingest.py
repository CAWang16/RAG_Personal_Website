"""
ingest.py — One-time script to chunk, embed, and upsert your
knowledge-base markdown files into Pinecone.

Run once (and re-run whenever you update your .md files):
    pip install pinecone google-generativeai python-dotenv
    python ingest.py
"""

import os
import re
import time
import hashlib
from pathlib import Path
from dotenv import load_dotenv

import google.generativeai as genai
from pinecone import Pinecone, ServerlessSpec

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
KNOWLEDGE_DIR   = "./knowledge-base"   # folder with your .md files
CHUNK_SIZE      = 400                  # words per chunk
CHUNK_OVERLAP   = 50                   # words overlap between chunks
EMBED_MODEL     = "models/text-embedding-004"
EMBED_DIM       = 768
PINECONE_INDEX  = os.getenv("PINECONE_INDEX", "portfolio")
BATCH_SIZE      = 50                   # upsert batch size (Pinecone limit: 100)
# ──────────────────────────────────────────────────────────────────────────────


def load_markdown_files(directory: str) -> list[dict]:
    """Read all .md files and return list of {filename, content} dicts."""
    docs = []
    for path in sorted(Path(directory).glob("**/*.md")):
        text = path.read_text(encoding="utf-8").strip()
        if text:
            docs.append({"filename": path.name, "filepath": str(path), "content": text})
            print(f"  Loaded: {path.name} ({len(text.split())} words)")
    return docs


def clean_text(text: str) -> str:
    """Normalize whitespace and strip markdown syntax noise."""
    text = re.sub(r"#{1,6}\s+", "", text)          # remove headings hashes
    text = re.sub(r"\*{1,2}(.+?)\*{1,2}", r"\1", text)  # remove bold/italic
    text = re.sub(r"`{1,3}[^`]*`{1,3}", "", text)  # remove inline code
    text = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", text) # links → text only
    text = re.sub(r"\n{3,}", "\n\n", text)          # collapse extra newlines
    return text.strip()


def chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Split text into overlapping word-level chunks."""
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk = " ".join(words[start:end])
        if len(chunk.strip()) > 30:   # skip tiny fragments
            chunks.append(chunk)
        start += chunk_size - overlap
    return chunks


def make_chunk_id(filename: str, chunk_index: int) -> str:
    """Stable, unique ID for each chunk based on filename + position."""
    raw = f"{filename}::{chunk_index}"
    return hashlib.md5(raw.encode()).hexdigest()


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Call Gemini embedding API. Retries once on rate-limit."""
    result = genai.embed_content(
        model=EMBED_MODEL,
        content=texts,
        task_type="retrieval_document",
    )
    return result["embedding"] if isinstance(texts, str) else result["embedding"]


def batch_embed(texts: list[str], batch_size: int = 20) -> list[list[float]]:
    """Embed in small batches to stay within API limits."""
    all_embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        try:
            embeddings = embed_texts(batch)
            all_embeddings.extend(embeddings)
        except Exception as e:
            print(f"  Embedding error on batch {i//batch_size}: {e}. Retrying in 5s...")
            time.sleep(5)
            embeddings = embed_texts(batch)
            all_embeddings.extend(embeddings)
        time.sleep(0.3)  # small delay to respect rate limits
    return all_embeddings


def upsert_to_pinecone(index, vectors: list[dict]):
    """Upsert vectors in batches."""
    for i in range(0, len(vectors), BATCH_SIZE):
        batch = vectors[i : i + BATCH_SIZE]
        index.upsert(vectors=batch)
        print(f"  Upserted batch {i//BATCH_SIZE + 1} ({len(batch)} vectors)")
        time.sleep(0.2)


def main():
    print("\n=== Portfolio RAG Ingestion ===\n")

    # ── 1. Init Gemini ──────────────────────────────────────────────────────
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    print("Gemini ready.")

    # ── 2. Init Pinecone ────────────────────────────────────────────────────
    pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))

    if PINECONE_INDEX not in [idx.name for idx in pc.list_indexes()]:
        print(f"Creating Pinecone index '{PINECONE_INDEX}'...")
        pc.create_index(
            name=PINECONE_INDEX,
            dimension=EMBED_DIM,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )
        time.sleep(5)  # wait for index to initialize

    index = pc.Index(PINECONE_INDEX)
    print(f"Pinecone index '{PINECONE_INDEX}' ready.")

    # ── 3. Load markdown files ──────────────────────────────────────────────
    print(f"\nLoading markdown files from '{KNOWLEDGE_DIR}'...")
    docs = load_markdown_files(KNOWLEDGE_DIR)
    if not docs:
        print("No .md files found. Check your KNOWLEDGE_DIR path.")
        return
    print(f"Loaded {len(docs)} files.\n")

    # ── 4. Chunk all docs ───────────────────────────────────────────────────
    print("Chunking documents...")
    all_chunks = []  # list of {id, text, metadata}
    for doc in docs:
        clean = clean_text(doc["content"])
        chunks = chunk_text(clean, CHUNK_SIZE, CHUNK_OVERLAP)
        for i, chunk_text_content in enumerate(chunks):
            all_chunks.append({
                "id":       make_chunk_id(doc["filename"], i),
                "text":     chunk_text_content,
                "metadata": {
                    "source":    doc["filename"],
                    "chunk_idx": i,
                    "text":      chunk_text_content,  # stored for retrieval
                },
            })

    print(f"Total chunks: {len(all_chunks)}\n")

    # ── 5. Embed all chunks ─────────────────────────────────────────────────
    print("Embedding chunks (this may take a minute)...")
    texts = [c["text"] for c in all_chunks]
    embeddings = batch_embed(texts, batch_size=20)
    print(f"Embedded {len(embeddings)} chunks.\n")

    # ── 6. Build vectors for Pinecone ───────────────────────────────────────
    vectors = [
        {
            "id":       chunk["id"],
            "values":   embedding,
            "metadata": chunk["metadata"],
        }
        for chunk, embedding in zip(all_chunks, embeddings)
    ]

    # ── 7. Upsert to Pinecone ───────────────────────────────────────────────
    print("Upserting to Pinecone...")
    upsert_to_pinecone(index, vectors)

    # ── 8. Verify ───────────────────────────────────────────────────────────
    stats = index.describe_index_stats()
    print(f"\nDone. Index now contains {stats['total_vector_count']} vectors.")
    print("\n=== Ingestion complete. Ready for Step 3 (RAG API). ===\n")


if __name__ == "__main__":
    main()