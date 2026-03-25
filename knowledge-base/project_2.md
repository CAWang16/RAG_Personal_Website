# Project: RAG Portfolio Chatbot

## Summary

A personal portfolio website with an embedded AI assistant powered by **Retrieval-Augmented Generation (RAG)**. The chatbot answers questions about Anders' background, experience, and projects by retrieving relevant context from a structured knowledge base before generating a response.

**Live at:** Deployed on Vercel (serverless)

---

## The Problem It Solves

Static portfolio websites can't answer follow-up questions or explain nuance. A recruiter might wonder: *"Has he worked with AWS Glue specifically for fraud detection?"* — a standard portfolio page can't respond. This chatbot can.

---

## Architecture & Stack

### Retrieval Pipeline
1. **User query** arrives at the FastAPI `/api/chat` endpoint
2. Query is embedded using **Gemini `gemini-embedding-001`** (3072-dimensional vectors)
3. Embedded vector is queried against a **Pinecone serverless index** (cosine similarity, top-4 results, min score 0.4)
4. Matching knowledge base chunks are returned as context

### Generation Pipeline
5. Retrieved context + conversation history are assembled into a structured prompt
6. Prompt is sent to **Groq's Llama 3.3-70B** (`llama-3.3-70b-versatile`) for streaming generation
7. Response is streamed back to the browser via **Server-Sent Events (SSE)**

### Frontend
- Floating chat widget built in vanilla JavaScript
- Real-time token streaming with blinking cursor during generation
- Markdown rendering via `marked.js` (bold, bullet lists, code blocks)
- Suggested questions on first open

---

## Knowledge Base

The RAG system is grounded in structured Markdown documents covering:
- **resume.md** — full work history with metrics and skills
- **about.md** — career narrative and motivation
- **skills.md** — detailed technical skills breakdown
- **project_1.md** — Amazon Review Quality Ranking deep-dive
- **project_2.md** — this document

Documents are chunked (400 words, 50-word overlap), embedded with Gemini, and upserted to Pinecone using MD5-based deterministic IDs (safe to re-run).

---

## Technical Highlights

### Async Streaming with Sync SDK
Groq's Python SDK is synchronous, but FastAPI requires async generators for `StreamingResponse`. The solution: run the Groq stream in a background thread and pass chunks through an `asyncio.Queue`, bridged with `asyncio.run_coroutine_threadsafe`.

### Rate Limiting
In-memory sliding-window rate limiter (Python `threading.Lock` + `defaultdict`):
- **5 requests per minute** per IP
- **50 requests per day** per IP
- Graceful 429 error messages displayed in the chat UI

### Deployment
- `vercel.json` routes `/api/*` to the Python FastAPI serverless function
- Static frontend served from `public/` directory
- Environment variables: `GEMINI_API_KEY`, `GROQ_API_KEY`, `PINECONE_API_KEY`

---

## Tech Stack Summary

| Layer | Technology |
|---|---|
| Embedding | Gemini `gemini-embedding-001` |
| Vector DB | Pinecone (serverless, cosine) |
| LLM | Groq `llama-3.3-70b-versatile` |
| Backend | FastAPI + Python |
| Streaming | Server-Sent Events (SSE) |
| Frontend | Vanilla JS + marked.js |
| Deployment | Vercel |

---

## Keywords

RAG | Retrieval-Augmented Generation | LLM | Groq | Llama | Pinecone | Vector Database | Gemini | Embeddings | FastAPI | Streaming | SSE | Server-Sent Events | Python | Vercel | Serverless | Chatbot | Portfolio | Rate Limiting | NLP
