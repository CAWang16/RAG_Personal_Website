"""
chat.py — FastAPI RAG endpoint for the portfolio chatbot.

Endpoints:
  POST /api/chat   — embed query → retrieve from Pinecone → stream Groq answer
  GET  /api/health — connectivity check
"""

import os
import time
import threading
import asyncio
from collections import defaultdict
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

from google import genai
from pinecone import Pinecone
from groq import Groq

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
EMBED_MODEL    = "models/gemini-embedding-001"
GROQ_MODEL     = "llama-3.3-70b-versatile"
PINECONE_INDEX = os.getenv("PINECONE_INDEX", "portfolio")
TOP_K          = 4
MIN_SCORE      = 0.4
MAX_TOKENS     = 512
TEMPERATURE    = 0.3
RATE_LIMIT_PER_MINUTE = 5    # max requests per IP per minute
RATE_LIMIT_PER_DAY    = 50   # max requests per IP per day
# ──────────────────────────────────────────────────────────────────────────────

# ── Rate limiter ──────────────────────────────────────────────────────────────
_rate_data: dict[str, list[float]] = defaultdict(list)
_rate_lock = threading.Lock()

def check_rate_limit(ip: str) -> None:
    """Raise 429 if the IP has exceeded per-minute or per-day limits."""
    now = time.time()
    with _rate_lock:
        timestamps = _rate_data[ip]
        timestamps[:] = [t for t in timestamps if now - t < 86400]
        per_minute = sum(1 for t in timestamps if now - t < 60)
        per_day    = len(timestamps)
        if per_minute >= RATE_LIMIT_PER_MINUTE:
            raise HTTPException(
                status_code=429,
                detail="Too many requests. Please wait a moment before asking again.",
            )
        if per_day >= RATE_LIMIT_PER_DAY:
            raise HTTPException(
                status_code=429,
                detail="Daily limit reached. Please come back tomorrow.",
            )
        timestamps.append(now)
# ──────────────────────────────────────────────────────────────────────────────

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-RAG-Sources"],
)

app.mount("/public", StaticFiles(directory="public", html=True), name="static")

# Lazy-init clients
_gemini_client = None
_groq_client   = None
_pinecone_index = None


def get_gemini() -> genai.Client:
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    return _gemini_client


def get_groq() -> Groq:
    global _groq_client
    if _groq_client is None:
        _groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    return _groq_client


def get_index():
    global _pinecone_index
    if _pinecone_index is None:
        pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        _pinecone_index = pc.Index(PINECONE_INDEX)
    return _pinecone_index


# ── Request / Response models ─────────────────────────────────────────────────

class Message(BaseModel):
    role: str      # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[Message] = []


# ── RAG helpers ───────────────────────────────────────────────────────────────

SYSTEM_PROMPT = (
    "You are a helpful assistant representing Anders (Cheng An) Wang's portfolio. "
    "Answer questions about Anders based ONLY on the context provided below. "
    "If the context does not contain enough information to answer, say so honestly "
    "rather than guessing. Be conversational, concise, and friendly. "
    "Do not invent facts, dates, or experiences not present in the context."
)


def embed_query(text: str) -> list[float]:
    client = get_gemini()
    response = client.models.embed_content(
        model=EMBED_MODEL,
        contents=[text],
    )
    return response.embeddings[0].values


def retrieve_context(query_vector: list[float]) -> tuple[list[str], list[str]]:
    """Return (text_chunks, source_filenames) for matches above MIN_SCORE."""
    index = get_index()
    results = index.query(
        vector=query_vector,
        top_k=TOP_K,
        include_metadata=True,
    )
    chunks, sources = [], []
    for match in results.matches:
        if match.score >= MIN_SCORE:
            chunks.append(match.metadata.get("text", ""))
            src = match.metadata.get("source", "")
            if src and src not in sources:
                sources.append(src)
    return chunks, sources


def build_messages(
    message: str,
    context_chunks: list[str],
    history: list[Message],
) -> list[dict]:
    """Build an OpenAI-style messages list for Groq."""
    context_text = (
        "\n\n---\n\n".join(context_chunks)
        if context_chunks
        else "No relevant context found."
    )
    system = f"{SYSTEM_PROMPT}\n\n<context>\n{context_text}\n</context>"

    msgs = [{"role": "system", "content": system}]
    for turn in history[-8:]:
        msgs.append({"role": turn.role, "content": turn.content})
    msgs.append({"role": "user", "content": message})
    return msgs


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.post("/api/chat")
async def chat(request: ChatRequest, req: Request):
    check_rate_limit(req.client.host)

    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    try:
        query_vector = embed_query(request.message)
        context_chunks, sources = retrieve_context(query_vector)
        messages = build_messages(request.message, context_chunks, request.history)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    async def event_stream():
        loop = asyncio.get_event_loop()
        q: asyncio.Queue = asyncio.Queue()

        def _stream_in_thread():
            try:
                client = get_groq()
                stream = client.chat.completions.create(
                    model=GROQ_MODEL,
                    messages=messages,
                    max_tokens=MAX_TOKENS,
                    temperature=TEMPERATURE,
                    stream=True,
                )
                for chunk in stream:
                    text = chunk.choices[0].delta.content or ""
                    asyncio.run_coroutine_threadsafe(q.put(text), loop)
            except Exception as exc:
                asyncio.run_coroutine_threadsafe(q.put(f"[ERROR] {exc}"), loop)
            finally:
                asyncio.run_coroutine_threadsafe(q.put(None), loop)

        threading.Thread(target=_stream_in_thread, daemon=True).start()

        while True:
            text = await q.get()
            if text is None:
                break
            if text:
                yield f"data: {text}\n\n"
        yield "data: [DONE]\n\n"

    headers = {"X-RAG-Sources": ", ".join(sources)}
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers=headers,
    )


@app.get("/api/health")
def health():
    try:
        index = get_index()
        stats = index.describe_index_stats()
        return {
            "status": "ok",
            "index": PINECONE_INDEX,
            "vector_count": stats["total_vector_count"],
            "embed_model": EMBED_MODEL,
            "gen_model": GROQ_MODEL,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
