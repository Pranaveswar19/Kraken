# Done

## Block 1: MCP Hello World (2025-12-12)

**Status:** PASS ✅  
**Deliverable:** Working MCP server with stdio transport  
**Key metrics:** ~500ms latency, tool called autonomously

## Block 2: Vector Search POC (2025-12-12)

**Status:** CONDITIONAL PASS ✅  
**Deliverable:** Vector search validated (84% relevance)  
**Key learning:** Cache critical (1500ms → 120ms)

## Block 3: MCP Integration (2025-12-16)

**Status:** PASS ✅  
**Deliverable:** Modular architecture, search_messages tool  
**Time:** 8 hours (config + async debugging)

## Block 4: Slack Integration (2025-12-17)

**Status:** PASS ✅  
**Deliverable:** SlackSyncService, slack_messages table, real data  
**Key optimization:** Batch user lookup (111x speedup)

## Block 5: Background Sync Service (2025-12-27 to 2026-01-08)

**Status:** PASS ✅  
**Deliverable:** APScheduler with incremental sync, no duplicates  
**Time:** 20 hours across 4 weeks

**What works:**

- ✅ Scheduler runs every 5 minutes (configurable)
- ✅ Incremental sync (timestamp-based filtering)
- ✅ No duplicates (UNIQUE constraint + upsert)
- ✅ State tracking (.cache/slack_sync_state.json)
- ✅ Retry logic (exponential backoff)
- ✅ Failure tracking (alerts on patterns)
- ✅ Batch enrichment (111x speedup)
- ✅ Graceful shutdown (Ctrl+C on Windows)

**Key fixes during block:**

- Fixed Windows signal handling (BackgroundScheduler + manual loop)
- Added client-side timestamp filtering
- Pagination loop (fetch all pages, not just first 100)
- Per-channel state tracking

---

# Now

## Block 6: Technical Debt Clearance (4-6 hours)

**Goal:** Make current MVP production-ready by fixing blocking scalability issues.

### Priority 1: Server-Side Filtering (1 hour)

**Problem:** Fetches ALL messages from Slack, filters in Python  
**Current waste:** 1000 messages fetched, 2 used = 998 wasted API calls  
**Impact:** Will hit Slack rate limits at 10+ customers

**Tasks:**

- [ ] Add `oldest` parameter to `SlackSyncService.fetch_messages()`
- [ ] Pass `last_ts` to Slack API (server-side filtering)
- [ ] Remove client-side filtering in `scheduler.py`
- [ ] Test: Verify logs show "Fetched 2 messages" not "Fetched 1000, filtered 998"

**Files changed:**

- `src/kraken/slack_sync.py` (add parameter)
- `src/kraken/scheduler.py` (use parameter, remove filter)

**Success criteria:**

- Slack API receives `oldest` parameter
- Only new messages returned by API
- 99% reduction in API calls

---

### Priority 2: pgvector RPC Search (2 hours)

**Problem:** Fetches all rows to client, calculates similarity in Python (O(n))  
**Current scale limit:** 10k messages = 5-10s search time (unacceptable)  
**Impact:** Search breaks at scale, customers churn

**Tasks:**

- [ ] Create Supabase RPC function `match_slack_messages()`
- [ ] Update `vector_store.py` to call RPC instead of client-side search
- [ ] Test with 1k+ messages, measure latency improvement
- [ ] Verify HNSW index is actually used (check EXPLAIN ANALYZE)

**Files changed:**

- Supabase SQL: Create RPC function
- `src/kraken/vector_store.py` (replace search logic)

**Success criteria:**

- Search time <100ms for 10k messages
- EXPLAIN ANALYZE shows HNSW index scan
- 10x latency improvement

**SQL to create:**

```sql
CREATE OR REPLACE FUNCTION match_slack_messages(
    query_embedding vector(1536),
    match_threshold float,
    match_count int
)
RETURNS TABLE (
    id bigint,
    content text,
    author text,
    channel text,
    permalink text,
    similarity float
)
LANGUAGE sql STABLE
AS $$
    SELECT
        id,
        content,
        author,
        channel,
        permalink,
        1 - (embedding <=> query_embedding) AS similarity
    FROM slack_messages
    WHERE 1 - (embedding <=> query_embedding) > match_threshold
    ORDER BY embedding <=> query_embedding
    LIMIT match_count;
$$;
```

---

### Priority 3: Similarity Threshold (5 minutes)

**Problem:** Returns 24% similarity matches (noise)  
**Impact:** Poor result quality, users lose trust

**Tasks:**

- [ ] Set `MIN_SIMILARITY_THRESHOLD = 0.35` in config
- [ ] Test: Query "hello" should NOT return random messages
- [ ] Validate with 5 test queries, check relevance improves

**Files changed:**

- `src/kraken/config.py` (or `.env`)

**Success criteria:**

- Only results >35% similarity returned
- Test queries: 80%+ relevant results

---

### Priority 4: Return Permalinks (30 minutes)

**Problem:** Results show snippets but can't click to original  
**Impact:** Users can't validate sources, poor UX

**Tasks:**

- [ ] Modify `vector_store.py` to return `permalink` field
- [ ] Update `mcp_server.py` to format as Markdown links
- [ ] Test: Click link in Claude, opens Slack message

**Files changed:**

- `src/kraken/vector_store.py` (include permalink in SELECT)
- `src/kraken/mcp_server.py` (format as `[View original](url)`)

**Success criteria:**

- Claude displays clickable links
- Links open correct Slack message
- Works for all result types

---

### Post-Block Validation

**Test suite (15 minutes):**

1. Sync channel with 500 messages
2. Run 10 search queries
3. Verify:
   - [ ] Search <100ms
   - [ ] Results >35% similarity
   - [ ] Permalinks clickable
   - [ ] Only new messages synced on repeat

**Metrics targets:**

- Search latency p95: <200ms (currently: ~1s)
- Sync API calls: 2-5 per run (currently: 100+)
- Result relevance: >70% (currently: ~40%)

---

## Block 6 Technical Debt Summary

**Before Block 6:**
| Issue | Impact | Scale Limit |
|-------|--------|-------------|
| Client-side filter | 998 wasted API calls | 10 customers (rate limits) |
| Client-side search | O(n) slow | 10k messages (>5s search) |
| Threshold 0.0 | Noise results | User trust loss |
| No permalinks | Can't validate | Poor UX |

**After Block 6:**
| Issue | Solution | New Limit |
|-------|----------|-----------|
| Client-side filter | Slack API `oldest` | 100k+ customers |
| Client-side search | pgvector RPC + HNSW | 1M+ messages |
| Threshold 0.35 | Quality filter | 80%+ relevance |
| Permalinks | Return + format | Validated sources |

**Total time:** 4-6 hours  
**Value:** MVP → Production-ready

---

# Next

## Block 7: Google Drive Integration (6-8 hours)

**Why Drive before Discord:**

- Broader market (100% companies use Drive vs 20% use Discord)
- Different content type (validates architecture handles documents)
- Higher customer value (documents > chat)

**Deliverables:**

- `GoogleDriveSyncService` class
- `gdrive_documents` table with chunking support
- Text extraction (PDFs, Docs, Sheets)
- Multi-source search in MCP (Slack + Drive)

**Defer to Month 2:**

- Discord integration (niche)
- GitHub integration (validate with customers first)

---

## Block 8: Deployment Packaging (4 hours)

**Why after debt clearance:**

- Don't deploy broken code
- Customers need production-ready, not MVP

**Deliverables:**

- Docker + docker-compose
- DEPLOYMENT.md guide
- Health check endpoints
- Monitoring/alerting setup

**Success criteria:**

- Customer deploys in <30 min
- Zero support tickets for setup

---

# Technical Debt Registry

## CLEARED (Block 6)

- ~~Client-side message filtering~~ → Server-side (Slack API `oldest`)
- ~~Client-side vector search~~ → pgvector RPC + HNSW
- ~~Similarity threshold 0.0~~ → Set to 0.35
- ~~No permalinks~~ → Return + format in results

## Deferred (Low Priority)

**Reason:** Not blocking MVP, fix if becomes problem

- Synchronous search (single-user OK, add ThreadPoolExecutor at 100+ concurrent)
- Upsert UPDATE mode (10ms overhead, negligible)
- Single embedding model (vendor lock-in, revisit at Month 2-3)
- No real-time sync (5-min lag acceptable, consider WebSocket at Month 3-4)
- Structured logging (add after first production incident)

## Future (Post-MVP)

- OAuth flow (manual setup OK for self-hosted)
- Multi-tenant routing (self-hosted = no sharing)
- Web UI (validate demand first)

---

# Metrics Targets

## MVP (End of Block 8)

- Uptime: 99% (3.6 days/year downtime acceptable for MVP)
- Search relevance: >70% (validated with test queries)
- Search latency p95: <500ms (cached <200ms)
- Sync lag: <5 min (incremental sync)
- Deployment time: <30 min (single command)
- Beta customers: 5-10 (validate PMF)

## v1.0 (Month 3)

- Uptime: 99.9% (43 min/month downtime)
- Relevance: >80% (tune threshold + model)
- Latency p95: <200ms all queries
- Scale: 100k messages per customer
- Customers: 50+ paying

---

# Questions to Validate

## Block 6 (Technical Debt)

- [ ] Does `oldest` parameter actually reduce API calls? (measure in logs)
- [ ] Is pgvector RPC actually faster? (benchmark before/after)
- [ ] Does 0.35 threshold improve relevance? (test 10 queries, compare)
- [ ] Do permalinks work in Claude Desktop? (manual test)

## Block 7 (Google Drive)

- [ ] Can we extract text from all file types? (PDF, Docx, Sheets, Slides)
- [ ] How to chunk 50-page documents? (fixed size, semantic breaks, or heading-based?)
- [ ] Does multi-source search confuse Claude? (Slack vs Drive formatting)

## Block 8 (Deployment)

- [ ] Can non-technical person deploy? (watch 3 people, measure time)
- [ ] What are top 3 failure modes? (document + fix)
- [ ] Is $20-50/month infrastructure cost acceptable? (customer feedback)
