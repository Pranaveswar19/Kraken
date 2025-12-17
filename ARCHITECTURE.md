# Architecture

## Problem

Engineers waste hours searching Slack/GitHub/Drive. Keyword search misses semantic matches.

## Solution

Ask Claude in natural language → Get results with sources.

## Stack

- **MCP Server:** Python, stdio transport, calls Backend API
- **Backend API:** FastAPI, routes to customer schema
- **Vector DB:** Supabase pgvector, schema-per-customer isolation
- **Embeddings:** OpenAI text-embedding-3-small ($0.02/1M tokens)
- **Sync:** APScheduler, hourly Slack/GitHub/Drive poll

## Diagrams

See `docs/` folder for Whimsical exports:

- `system-architecture.png`: Component overview
- `search-flow.png`: User query → results
- `sync-flow.png`: Background data ingestion

## Key Decisions

1. **MCP stdio:** Only option for Claude Desktop (no SSE yet)
2. **Schema-per-customer:** $25/month for all vs $12.5k/month for DB-per-customer
3. **OpenAI embeddings:** $100/month at scale vs GPU ops burden
4. **Hourly sync:** Simple vs real-time (sufficient for MVP)

## Performance

- Search latency: ~350ms (embedding 200ms + pgvector 50ms + network 100ms)
- Sync throughput: 5,000 messages/min (Slack rate limit)
- Storage: ~61MB per 10k messages (1MB text + 60MB vectors)

## Cost at 500 Customers

- Supabase: $28/month (8GB Pro plan)
- OpenAI: $100/month (50M messages)
- Railway: $50/month (API + Sync)
- **Total: $178/month** (0.015% of $1.2M ARR)
