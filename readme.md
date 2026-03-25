# RAG Portfolio Website

A personal portfolio website with an AI-powered chatbot that answers questions about you — your projects, skills, and experience — using Retrieval-Augmented Generation (RAG). Visitors can have a natural conversation with your portfolio instead of just reading static pages.

**Total monthly cost: ~$1/month** (domain only — all services run on free tiers).

---

## Table of Contents

- [RAG Portfolio Website](#rag-portfolio-website)
  - [Table of Contents](#table-of-contents)
  - [How It Works](#how-it-works)
  - [Tech Stack](#tech-stack)
  - [Project Structure](#project-structure)
  - [Prerequisites](#prerequisites)
  - [Setup Guide](#setup-guide)
    - [1. Clone and install dependencies](#1-clone-and-install-dependencies)
    - [2. Get your API keys](#2-get-your-api-keys)
    - [3. Configure environment variables](#3-configure-environment-variables)
    - [4. Write your knowledge base](#4-write-your-knowledge-base)
    - [5. Run the ingestion script](#5-run-the-ingestion-script)
    - [6. Run the API locally](#6-run-the-api-locally)
    - [7. Deploy to Vercel](#7-deploy-to-vercel)
  - [API Reference](#api-reference)
    - [`POST /api/chat`](#post-apichat)
    - [`GET /api/health`](#get-apihealth)
  - [Knowledge Base Guide](#knowledge-base-guide)
    - [`about.md`](#aboutmd)
    - [`resume.md`](#resumemd)
    - [`skills.md`](#skillsmd)
    - [`project_X.md`](#project_xmd)
  - [Configuration Reference](#configuration-reference)
  - [Updating Your Content](#updating-your-content)
  - [Cost Breakdown](#cost-breakdown)
  - [Troubleshooting](#troubleshooting)
  - [Roadmap](#roadmap)

---

## How It Works

When a visitor asks a question in the chat widget, the following pipeline runs:

```
User question
     │
     ▼
Embed question          ← Gemini gemini-embedding-001 (3072-dim vector)
     │
     ▼
Query Pinecone          ← cosine similarity search, top-4 chunks, score ≥ 0.4
     │
     ▼
Build prompt            ← system prompt + retrieved context + conversation history
     │
     ▼
Generate answer         ← Gemini 2.0 Flash, streamed token-by-token
     │
     ▼
Stream to browser       ← Server-Sent Events (SSE)
```

The chatbot only answers from your knowledge base — it cannot hallucinate facts about you because the system prompt strictly grounds it to the retrieved context. If a question falls outside your documents, it says so honestly.

---

## Tech Stack

| Layer | Service | Free tier |
|---|---|---|
| Frontend hosting | Vercel | 100 GB bandwidth/month |
| LLM | Gemini 2.0 Flash | 1,500 requests/day |
| Embeddings | Gemini gemini-embedding-001 | Included with Gemini free tier |
| Vector database | Pinecone Starter | 2 GB storage, 1 index |
| RAG framework | LangChain (optional) / custom | Open source |
| Backend | FastAPI on Vercel serverless | 100k invocations/month |
| Design | Figma Free | 3 projects |
| Domain | Namecheap / Cloudflare | ~$10–12/year |

---

## Project Structure

```
RAG_website/
│
├── knowledge-base/             # Your personal content (edit these)
│   ├── about.md                # Bio, background, goals
│   ├── resume.md               # Education, experience, timeline
│   ├── skills.md               # Tools, technologies, depth of expertise
│   └── project_1.md            # One file per project (add more as needed)
│
├── api/
│   └── chat.py                 # FastAPI RAG endpoint (Vercel serverless)
│
├── public/                     # Frontend static files (Step 4)
│   ├── index.html
│   ├── style.css
│   └── chat.js                 # Chat widget (Step 5)
│
├── ingest.py                   # One-time ingestion script
├── vercel.json                 # Vercel deployment config
├── requirements.txt            # Python dependencies
├── .env                        # Local secrets (never commit this)
├── .env.example                # Safe template to commit
├── .gitignore
└── README.md
```

---

## Prerequisites

- Python 3.10+ (3.9 works but is end-of-life — upgrade recommended)
- A [Pinecone](https://pinecone.io) account (free)
- A [Google AI Studio](https://aistudio.google.com) account (free)
- A [Vercel](https://vercel.com) account (free)
- A [GitHub](https://github.com) account (for Vercel deployment)

---

## Setup Guide

### 1. Clone and install dependencies

```bash
git clone https://github.com/yourusername/RAG_website.git
cd RAG_website

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

`requirements.txt`:
```
fastapi
uvicorn
python-dotenv
pinecone
google-genai
pydantic
```

---

### 2. Get your API keys

**Pinecone**
1. Sign up at [pinecone.io](https://pinecone.io)
2. Go to **API Keys** in the sidebar → copy your key
3. The ingestion script will create the index automatically on first run

**Gemini**
1. Go to [aistudio.google.com](https://aistudio.google.com)
2. Click **Get API key** → **Create API key**
3. Copy the key — you won't be able to see it again

---

### 3. Configure environment variables

Create a `.env` file in the project root (never commit this file):

```bash
cp .env.example .env
```

Edit `.env`:
```env
GEMINI_API_KEY=your_gemini_api_key_here
PINECONE_API_KEY=your_pinecone_api_key_here
PINECONE_INDEX=portfolio
```

`.env.example` (safe to commit):
```env
GEMINI_API_KEY=
PINECONE_API_KEY=
PINECONE_INDEX=portfolio
```

Add `.env` to your `.gitignore`:
```
.env
venv/
__pycache__/
*.pyc
```

---

### 4. Write your knowledge base

The quality of the chatbot is entirely determined by how well you describe yourself in the `knowledge-base/` folder. Write in complete sentences — the LLM retrieves chunks of text and uses them verbatim as context.

See the [Knowledge Base Guide](#knowledge-base-guide) section for detailed templates.

---

### 5. Run the ingestion script

This is a one-time script (re-run it whenever you update your `.md` files):

```bash
python ingest.py
```

Expected output:
```
=== Portfolio RAG Ingestion ===

Pinecone index 'portfolio' ready.

Loading markdown files from './knowledge-base'...
  Loaded: about.md (458 words)
  Loaded: project_1.md (635 words)
  Loaded: resume.md (428 words)
  Loaded: skills.md (474 words)
Loaded 4 files.

Chunking documents...
Total chunks: 8

Embedding chunks (this may take a minute)...
Embedded 8 chunks.

Upserting to Pinecone...
  Upserted batch 1 (8 vectors)

Done. Index now contains 8 vectors.

=== Ingestion complete. Ready for Step 3 (RAG API). ===
```

What the script does under the hood:
- Reads all `.md` files from `knowledge-base/`
- Strips markdown formatting noise (headings, bold, links) before embedding
- Splits each document into 400-word chunks with 50-word overlap (so context isn't lost at boundaries)
- Embeds each chunk using `gemini-embedding-001` (3072 dimensions)
- Assigns each chunk a stable deterministic ID based on filename + position — safe to re-run without creating duplicates
- Upserts all vectors and metadata to Pinecone in batches of 50

---

### 6. Run the API locally

```bash
uvicorn api.chat:app --reload --port 8000
```

Test the health check:
```bash
curl http://localhost:8000/api/health
```
```json
{
  "status": "ok",
  "index": "portfolio",
  "vector_count": 8,
  "embed_model": "models/gemini-embedding-001"
}
```

Test the chat endpoint:
```bash
curl -X POST http://localhost:8000/api/chat \
     -H "Content-Type: application/json" \
     -d '{"message": "What projects have you worked on?"}'
```

You should see a streamed SSE response:
```
data: Based
data:  on
data:  the portfolio
data:  context...
data: [DONE]
```

To test with conversation history:
```bash
curl -X POST http://localhost:8000/api/chat \
     -H "Content-Type: application/json" \
     -d '{
       "message": "What tools did you use for that?",
       "history": [
         {"role": "user",      "content": "Tell me about your data pipeline project"},
         {"role": "assistant", "content": "The data pipeline project involved..."}
       ]
     }'
```

---

### 7. Deploy to Vercel

**Push to GitHub first:**
```bash
git add .
git commit -m "initial RAG portfolio setup"
git push origin main
```

**Deploy on Vercel:**
1. Go to [vercel.com](https://vercel.com) → **New Project**
2. Import your GitHub repository
3. Framework preset: **Other**
4. Add your environment variables under **Settings → Environment Variables**:
   - `GEMINI_API_KEY`
   - `PINECONE_API_KEY`
   - `PINECONE_INDEX` → `portfolio`
5. Click **Deploy**

Vercel reads `vercel.json` to route `/api/*` requests to `api/chat.py` as a Python serverless function.

**Connect a custom domain:**
1. Vercel dashboard → your project → **Settings → Domains**
2. Add your domain (e.g. `yourname.dev`)
3. Follow Vercel's DNS instructions for your registrar

> Note: Vercel serverless functions have a **10-second timeout** on the free plan. A typical RAG query (embed → retrieve → generate) completes in 3–5 seconds, well within this limit. Avoid running heavy preprocessing inside the endpoint.

---

## API Reference

### `POST /api/chat`

Accepts a user message and optional conversation history. Returns a streamed SSE response.

**Request body:**
```json
{
  "message": "What data engineering tools do you know?",
  "history": [
    {"role": "user",      "content": "previous question"},
    {"role": "assistant", "content": "previous answer"}
  ]
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `message` | string | yes | The user's question |
| `history` | array of objects | no | Last N turns of conversation. Only the 4 most recent turns are used. |

**Response:** `text/event-stream` (SSE)

Each event is a token fragment:
```
data: Hello
data: , here
data:  is what I found...
data: [DONE]
```

**Response headers:**
| Header | Description |
|---|---|
| `X-RAG-Sources` | Comma-separated list of source `.md` files used to answer |

**Error responses:**
| Status | Meaning |
|---|---|
| 400 | Empty message |
| 500 | Embedding or generation error |

---

### `GET /api/health`

Health check. Confirms Pinecone connection and returns current vector count.

**Response:**
```json
{
  "status": "ok",
  "index": "portfolio",
  "vector_count": 8,
  "embed_model": "models/gemini-embedding-001"
}
```

---

## Knowledge Base Guide

Your `.md` files are the brain of the chatbot. More detail = better, more specific answers. Aim for 400–600 words per file minimum.

### `about.md`
```markdown
# About Me

My name is [Your Name]. I'm a data scientist and data engineer based in [City].
I'm currently pursuing a [degree] at [university], focusing on [specialization].

My background started in [field/origin story]. Over time I developed a strong
interest in [specific areas — e.g. building end-to-end ML pipelines, making data
accessible through visualization, working with large-scale streaming systems].

I'm currently looking for roles as a data scientist, data engineer, or data analyst
where I can [what you want to do]. I'm particularly interested in [industries/domains].

Outside of work, I enjoy [hobbies — makes the chatbot feel more human].
```

### `resume.md`
```markdown
# Resume

## Education
- [Degree], [University], [Year] — GPA [X.X if strong]
- Relevant courses: [list key courses]

## Work Experience

### [Job Title] at [Company] — [Dates]
[2–3 sentences describing what you actually did, tools used, and impact/outcomes]

## Certifications
- [Name], [Issuer], [Year]
```

### `skills.md`
```markdown
# Technical Skills

## Programming Languages
Python (advanced — pandas, numpy, scikit-learn, FastAPI), SQL (intermediate — joins,
window functions, CTEs), R (basic)

## Data Engineering
Experience building ETL pipelines with [tools]. Comfortable with [platforms].
Have worked with data at [scale — e.g. millions of rows, streaming data].

## Machine Learning
[Supervised/unsupervised methods you know]. Have applied [specific algorithms] to
[types of problems]. Familiar with model evaluation, cross-validation, and deployment.

## Visualization & BI
Plotly, Matplotlib, Tableau, Looker Studio. Focus on making insights accessible
to non-technical stakeholders.

## Tools & Platforms
Git, Docker, [cloud platform], [databases], [other tools].
```

### `project_X.md`
```markdown
# Project: [Project Name]

## Overview
[1–2 sentences: what problem does this solve and why does it matter?]

## My Role
[Were you solo or in a team? What were you specifically responsible for?]

## Problem
[Describe the challenge in detail. What was broken, missing, or inefficient?]

## Approach
[Walk through your methodology. What decisions did you make and why?]

## Tools & Technologies
- Language: Python
- Libraries: [list]
- Infrastructure: [list]
- Data sources: [describe]

## Results & Impact
[Concrete outcomes — numbers are best. "Reduced processing time by 40%",
"Model achieved 92% accuracy", "Dashboard used by 50+ stakeholders weekly"]

## What I Learned
[Honest reflection — shows growth mindset and self-awareness]

## Links
- GitHub: [url]
- Live demo: [url if applicable]
```

---

## Configuration Reference

Key constants in `ingest.py` and `api/chat.py` — both files must stay in sync:

| Parameter | File | Default | Description |
|---|---|---|---|
| `EMBED_MODEL` | both | `models/gemini-embedding-001` | Embedding model. Must be identical in both files. |
| `EMBED_DIM` | ingest.py | `3072` | Vector dimension. Must match the Pinecone index dimension. |
| `CHUNK_SIZE` | ingest.py | `400` | Words per chunk. Increase for more context per retrieval hit. |
| `CHUNK_OVERLAP` | ingest.py | `50` | Word overlap between chunks. Prevents context loss at boundaries. |
| `GEMINI_MODEL` | chat.py | `gemini-2.0-flash` | Generation model. Flash is fast and free-tier friendly. |
| `TOP_K` | chat.py | `4` | Number of chunks retrieved per query. |
| `MIN_SCORE` | chat.py | `0.4` | Minimum cosine similarity to include a chunk. Raise if answers feel off-topic. |
| `MAX_TOKENS` | chat.py | `512` | Max response length. Raise for longer answers. |
| `TEMPERATURE` | chat.py | `0.3` | Creativity level. Keep low (0.1–0.4) for factual portfolio answers. |

> **Critical:** `EMBED_MODEL` and `EMBED_DIM` must be identical in `ingest.py` and `api/chat.py`. If they diverge, queries will return garbage results because the query vector will be in a different space than the stored vectors.

---

## Updating Your Content

Whenever you add a new project, update your resume, or expand your skills file:

```bash
# 1. Edit your markdown files in knowledge-base/

# 2. Re-run ingestion (safe to re-run — IDs are deterministic, no duplicates)
python ingest.py

# 3. Verify the new vector count
curl http://localhost:8000/api/health

# 4. Commit and push — Vercel auto-redeploys
git add knowledge-base/
git commit -m "add project_2 to knowledge base"
git push
```

The deployed API on Vercel doesn't need to be redeployed — it reads from Pinecone at query time, so updated vectors are live immediately after ingestion.

---

## Cost Breakdown

| Service | Free tier | Overage cost |
|---|---|---|
| Vercel | 100 GB bandwidth, 100k function calls/month | $0.40/GB, $0.60/1M calls |
| Gemini API | 1,500 requests/day, 1M tokens/min | ~$0.075/1M tokens (Flash) |
| Pinecone Starter | 2 GB storage, 1 index | Next tier: $70/month |
| Domain name | — | ~$10–12/year (~$1/month) |
| **Total** | | **~$1/month** |

A personal portfolio realistically receives far fewer than 1,500 chat requests per day, so the Gemini free tier is essentially unlimited for this use case. Pinecone's 2 GB free tier holds hundreds of thousands of vectors — your knowledge base would need to be enormous to approach this limit.

---

## Troubleshooting

**`No relevant context found` in every response**
- Your `MIN_SCORE` threshold may be too high. Try lowering it to `0.3` in `chat.py`.
- Make sure `EMBED_MODEL` is identical in both `ingest.py` and `chat.py`.
- Verify vectors were upserted: `curl http://localhost:8000/api/health` should show `vector_count > 0`.

**Ingestion succeeds but answers are vague or wrong**
- Your `.md` files may be too short. Aim for 400+ words per file with specific details, tool names, and outcomes.
- Chunks of 400 words with 8 total chunks means ~4 files × 2 chunks each — that's quite lean. Expand your knowledge base.

**`FutureWarning: Python 3.9 past end of life`**
- Harmless, but upgrade to Python 3.11+ when convenient: `brew install python@3.11` on Mac.

**Vercel function timeout**
- Symptom: works locally but times out on Vercel.
- The free plan has a 10-second limit. Check if Pinecone or Gemini is slow to respond — usually a cold-start issue. The first request after a long idle period can be slow; subsequent ones are faster.

**CORS errors in the browser**
- `allow_origins=["*"]` in `chat.py` should prevent this during development.
- After deploying, replace `"*"` with your actual domain: `allow_origins=["https://yourname.dev"]`.

**Pinecone `dimension mismatch` error**
- Your Pinecone index was created with a different dimension than your embedding model produces.
- Fix: delete the index in the Pinecone dashboard and re-run `python ingest.py` — it will recreate it with the correct dimension (3072).

---

## Roadmap

- [x] Knowledge base (markdown documents)
- [x] Pinecone ingestion pipeline
- [x] RAG API endpoint with streaming
- [ ] Frontend portfolio site (Figma → HTML/CSS)
- [ ] Floating chat widget with SSE streaming
- [ ] Project gallery with embedded Plotly charts
- [ ] Vercel deployment + custom domain
- [ ] Suggested questions in chat UI
- [ ] Rate limiting on the API endpoint
- [ ] Analytics (which questions do visitors ask most?)