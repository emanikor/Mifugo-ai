# Mifugo AI

Offline-first livestock market intelligence for Turkana County, Kenya.

## Architecture

Every choice below is driven by one constraint: **this runs on a field
laptop with no reliable internet, possibly for weeks at a time.**

```
┌─────────────────┐      ┌──────────────────┐      ┌──────────────┐
│  frontend        │      │  backend          │      │  db            │
│  React + Vite    │─────▶│  FastAPI (JSON API)│─────▶│  PostgreSQL    │
│  :5173            │      │  :8000              │      │  :5432          │
└─────────────────┘      └──────────┬────────┘      └──────────────┘
                                      │
                                      ▼
                            ┌──────────────────┐
                            │  ollama            │
                            │  Llama 3.2 3B       │
                            │  :11434              │
                            └──────────────────┘
```

All four services run as Docker containers on the **same machine**, talking
to each other over the local Docker network. `docker compose build` is the
only step in this project's lifecycle that needs internet access — it pulls
base images and installs npm/pip packages once. After that, `docker compose
up` runs entirely offline.

| Concern      | Choice                                     | Reason |
|---------------|----------------------------------------------|--------|
| Frontend      | React + Vite, decoupled SPA                  | Per project requirement — built once via Docker, no runtime npm/CDN dependency after that |
| Backend       | FastAPI, pure JSON API                        | Lightweight, no build step, easy to containerize |
| Database      | PostgreSQL (own container, local volume)      | Durable, transactional, survives power loss |
| AI engine     | Ollama (own container) running Llama 3.2 3B   | Small enough for modest field hardware, fully offline |
| RAG retrieval | Structured SQL queries, not vector embeddings | Market data is numeric/structured — we retrieve exact rows (region, species, date range) and hand them to the LLM to phrase into natural language, rather than embedding text chunks. Keeps numbers exact and auditable. |
| Auth          | JWT bearer tokens                              | Standard for a decoupled SPA talking to a separate API origin; no external identity provider |

## Hard constraints baked into the design

- **No CDN links, no external fonts, no telemetry** anywhere in the frontend
  (see `frontend/index.html`, `frontend/vite.config.js`).
- **No cloud LLM fallback.** If Ollama isn't running, the chat feature fails
  loudly and explains why (`backend/app/rag/llm_client.py`) — it never
  silently calls out to the internet.
- **Crash-safe writes.** Price entries are committed as DB transactions in
  their own Postgres container with a persistent volume; a power cut mid-entry
  shouldn't corrupt data.
- **Outlier detection is transparent, not silent.** Flagged/rejected prices
  are stored with a reason code, never deleted — officials can audit and
  override every decision (`backend/app/outlier_detection.py`).
- **Non-technical users.** The React entry form favors big, forgiving inputs
  over dense data-grids (`frontend/src/pages/DataEntry.jsx`).

## One-time setup (needs internet)

```bash
# 1. Build all images — this is the only step requiring internet access
docker compose build

# 2. Start everything
docker compose up -d

# 3. Pull the LLM model into the ollama container (one-time, needs internet)
docker compose exec ollama ollama pull llama3.2:3b

# 4. Create your first admin/agent account
docker compose exec backend python -m scripts.seed_admin
```

Then open `http://localhost:5173` in a browser on the same machine.

## Everyday offline use (after the above, no internet needed)

```bash
docker compose up -d
# ... use the app at http://localhost:5173 ...
docker compose down          # when done, data persists in Docker volumes
```

## Project layout

```
docker-compose.yml       Orchestrates db / backend / frontend / ollama containers
backend/
  Dockerfile
  requirements.txt
  migrations/schema.sql   Hand-written SQL schema, auto-applied on first db start
  scripts/seed_admin.py   One-time CLI to create the first account(s)
  app/
    main.py               FastAPI app, CORS config, mounts routers
    config.py             Env-driven settings (DB url, JWT secret, Ollama url)
    database.py           SQLAlchemy engine/session
    models.py             ORM: Region, Species, Agent, PriceEntry
    schemas.py             Pydantic request/response contracts (API <-> React)
    security.py            JWT + password hashing
    outlier_detection.py  Statistical price validation, with audit trail
    routers/
      auth.py             Login (JWT issuance), /auth/me
      prices.py           Agent price-entry + official review endpoints
      chat.py             RAG chat endpoint
    rag/
      retriever.py         Pulls relevant rows from Postgres based on question
      llm_client.py         Thin wrapper around local Ollama HTTP API
      pipeline.py            Glues retriever + prompt template + llm_client together
frontend/
  Dockerfile
  package.json
  vite.config.js
  index.html
  src/
    main.jsx / App.jsx      App entry + routing + auth guard
    api/client.js            Single source of truth for backend calls
    components/Layout.jsx    Shared nav shell
    pages/
      Login.jsx
      DataEntry.jsx          Core agent workflow
      Dashboard.jsx           Recent prices + flagged-entry review
      Chat.jsx                 Natural-language RAG chat interface
    styles/index.css          System fonts only, large touch targets
```

## Status

This is a **stubbed scaffold**: structure, schema, auth, and the RAG pipeline
skeleton are wired end-to-end; some logic has clear `# TODO` markers where
deeper implementation goes next (see `outlier_detection.py` thresholds and
`rag/retriever.py` intent parsing in particular — both are deliberately
simple starting points to tune against real Turkana market data).

Nothing in this project calls the network except to the local Docker
services (db, ollama) and, once, at `docker compose build` time.
