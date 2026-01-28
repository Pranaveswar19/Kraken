# Components

## Core

**Python 3.11+**
Type hints, async native, performance.

**uv** (package manager)
10-100x faster than pip/poetry.

**MCP SDK** (`mcp`)
Anthropic's official SDK for Claude Desktop stdio integration.

## Storage

**Supabase** (`supabase`)
Managed Postgres + pgvector. Free tier: 500MB (8 customers). Pro: $25/month (8GB).
_Trade-off:_ Simpler ops vs higher cost at scale. Break-even: ~50M vectors.

**pgvector**
Vector similarity search extension. HNSW index: ~50ms for 100k vectors.
_Config:_ `m=16, ef_construction=64` (balance accuracy vs speed).

## AI

**OpenAI text-embedding-3-small** (`openai`)
1536 dims, $0.02/1M tokens, 200ms latency, 62.3% MTEB.
_Trade-off:_ Zero ops vs external dependency. Self-host if >$1k/month.

## Backend

**FastAPI** (`fastapi`)
Async, type validation (Pydantic), auto OpenAPI docs.

**APScheduler** (`apscheduler`)
Cron-like jobs, runs in-process, SQLite persistence.
_Trade-off:_ Simple vs distributed (use Celery if >10k customers).

## External APIs

**Slack API** (`slack-sdk`)
Rate limit: 50 req/min, 100 messages/page = 5k messages/min.

**GitHub API** (future: `PyGithub`)
**Google Drive API** (future: `google-api-python-client`)

## Deployment

**Railway**
Push-to-deploy, auto-scaling. $5/month minimum, ~$50/month for MVP.
_Trade-off:_ Fast deploy vs cost at scale (AWS cheaper at $200+/month).

---

## Not Using

**LangChain/LlamaIndex:** Abstraction bloat. We control the RAG pipeline.
**Celery:** Overkill for hourly jobs. APScheduler sufficient.
**Redis:** No caching/pub-sub need yet. Add if search >5s.
**Docker:** Railway handles deploy. Local dev uses uv.

```

**That's it. 40 lines. You understand everything.**

---

## Whimsical Diagrams (3 Files)

### 1. System Architecture

**What to draw:**
```

User Machine:
[Claude Desktop]
↓ stdio
[MCP Server (Python)]
↓ HTTPS

Cloud:
[Backend API (FastAPI)]
↓
[Supabase (pgvector)]
↑
[Sync Service (APScheduler)]
↓
External:
[Slack API]
[OpenAI API]
[GitHub API]

```

**Whimsical steps:**
1. New board → Flowchart
2. Add boxes (components)
3. Add arrows (data flow)
4. Color code: Blue (user), Green (your code), Orange (external APIs), Purple (storage)
5. Export → PNG → Save as `docs/system-architecture.png`

---

### 2. Search Flow

**What to draw:**
```

1. User types in Claude: "auth bug"
2. Claude Desktop spawns MCP server
3. MCP calls: search_messages("auth bug")
4. MCP → OpenAI API: Generate embedding (200ms)
5. MCP → Backend API: POST /search
6. Backend → Supabase: Vector similarity query (50ms)
7. Supabase returns top 5 results
8. Backend formats with metadata
9. MCP returns to Claude
10. Claude displays: "Sarah said in #eng..."

```

**Timeline format in Whimsical:**
- Use flowchart with vertical layout
- Add timing labels: "200ms", "50ms"
- Highlight bottlenecks (OpenAI embedding)

Export → `docs/search-flow.png`

---

### 3. Sync Flow

**What to draw:**
```

1. APScheduler triggers (every 60 min)
2. Sync Service: Fetch cursor from DB
3. Slack API: conversations.history(cursor)
4. Slack returns 100 messages + next_cursor
5. Batch: For each message
6. OpenAI API: Generate embeddings
7. Supabase: Batch insert messages + vectors
8. Update cursor in DB
9. Repeat until no more messages
