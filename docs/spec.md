# Kraken - Specification Document

**Version:** 0.1.0 (MVP)  
**Date:** December 2025  
**Status:** In Development (Block 5 - Phase 1 Complete)

---

## Overview

**What:** Claude Desktop extension that enables semantic search of Slack message history  
**Why:** Engineers waste hours searching Slack with keyword search missing semantic matches  
**How:** Vector embeddings + MCP protocol + self-hosted deployment

---

## Architecture

```
User asks Claude → MCP Server (stdio) → OpenAI embeddings → Supabase (pgvector) → Results
                                      ↓
                            Background Sync (hourly) ← Slack API
```

**Stack:**

- Python 3.13, MCP SDK, APScheduler
- OpenAI text-embedding-3-small (1536 dims, $0.02/1M tokens)
- Supabase PostgreSQL + pgvector (HNSW index)
- Slack Bot Token (channels:history, channels:read, users:read)

---

## Features

**Core (MVP):**

- Semantic search via Claude Desktop (`search_messages` tool)
- Hourly background sync (APScheduler + SQLite persistence)
- Batch embedding generation (40x faster than sequential)
- Persistent cache (92% latency reduction: 1500ms → 120ms)
- User enrichment (Slack IDs → real names)
- Deduplication (ON CONFLICT upsert)

**Deferred (Post-MVP):**

- OAuth flow (manual bot token setup for MVP)
- Multi-tenant schemas (self-hosted = physical isolation)
- Web UI (Claude Desktop only for MVP)
- Real-time sync (hourly sufficient for MVP)
- GitHub/Drive integration (Slack only for MVP)

---

## Deployment Model

**Self-Hosted (Chosen for MVP):**

- Customer creates own Supabase account (free tier: 500MB)
- Customer creates own Slack bot (5 min setup)
- Customer deploys via Docker (`docker-compose up`)
- Zero infrastructure costs for us, physical data isolation

---

## Performance Targets

**MVP (5 beta users):**

- Search latency: <500ms (cached), <2s (uncached)
- Sync lag: <60 min (hourly jobs)
- Relevance: >70% (with 0.35 similarity threshold)
- Deployment time: <30 min (one command)

**v1.0 (50 users):**

- Uptime: 99.9% (43 min/month downtime)
- Relevance: >80%
- Scale: 100k messages per customer

---

## Technical Decisions

| Decision               | Rationale                                            | Trade-off                           |
| ---------------------- | ---------------------------------------------------- | ----------------------------------- |
| Self-hosted            | Solves data isolation, $0 infra, enterprise-friendly | Manual onboarding vs auto SaaS      |
| Client-side search     | Supabase RPC issues, reliable                        | Doesn't scale >10k (fix Block 7)    |
| Persistent cache       | 92% latency ↓, cost savings                          | Disk space (~1KB/query, negligible) |
| APScheduler            | Simple, sufficient for hourly                        | Not distributed (Celery overkill)   |
| SQLite jobstore        | File-based, survives restarts                        | Not HA (PostgreSQL overkill)        |
| text-embedding-3-small | Cheap, fast, 84% relevance                           | Vendor lock-in (fix Month 2-3)      |

---

## Blocks (Development Plan)

**Done:**

- Block 1: MCP Hello World (stdio validated)
- Block 2: Vector Search POC (84% relevance, cache critical)
- Block 3: MCP Integration (modular architecture)
- Block 4: Slack Integration (batch embed 40x faster)
- Block 5: Background Sync (Phase 1/5 - basic scheduler working)

**Now:**

- Block 5: Phases 2-5 (integrate sync, CLI, error recovery, testing)

**Next:**

- Block 6: Docker Packaging (Dockerfile, docker-compose, deploy scripts)
- Block 7: Documentation (DEPLOYMENT.md, README.md, polish)

**Ship:** 5 beta users, 1 week

---

## Known Issues (Technical Debt)

**High Priority (MVP blockers):**

- Similarity threshold 0.0 → set to 0.35 (returns weak results)
- No permalinks → add Slack URLs (can't click to original)

**Medium Priority (fix if users complain):**

- Client-side search doesn't scale >10k messages
- Synchronous search blocks event loop (single-user OK)
- Upsert UPDATE mode wastes queries (~10ms)

**Low Priority (works fine):**

- No HNSW index usage (client-side defeats it)
- Global embedding cache (not per-customer)

---

## Files & Structure

```
src/kraken/          # Production code (imports)
  ├── config.py          # Env vars, validation
  ├── embeddings.py      # OpenAI + cache
  ├── vector_store.py    # Supabase + search
  ├── slack_sync.py      # Slack API integration
  ├── mcp_server.py      # MCP protocol (2 tools)
  └── scheduler.py       # APScheduler (NEW)

scripts/             # Dev/deployment tools
  ├── sync_slack.py      # Manual sync CLI
  └── run_scheduler.py   # Start background sync (NEW)

tests/               # Test data + reports
  └── block1-4.md        # Completion reports
```
