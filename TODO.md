## Done

- [x] Block 1: MCP Hello World (2025-12-12)

  - Status: PASS ✅
  - Test report: tests/block1-mcp-hello-world.md
  - Latency: ~500ms (p50)
  - Tool: get_timestamp (validates MCP protocol works)
  - Claude used tool autonomously
  - Config automation: scripts/setup_claude_config.py
  - Deliverable: Working MCP server with stdio transport

- [x] Block 2: Vector Search POC (2025-12-12)

  - Status: CONDITIONAL PASS ✅
  - Test report: tests/block2-vector-search-poc.md
  - Relevance: 84% (target: 80%) ✅
  - Latency Pass 1 (cold): 1914ms avg (OpenAI API slow, network-dependent)
  - Latency Pass 2 (warm): ~120ms avg (cached embeddings) ✅
  - Deliverables:
    - Supabase + pgvector configured
    - 20 test messages with embeddings
    - Standalone search script (scripts/test_vector_search.py)
    - Embedding cache system (persistent, 100% hit rate on repeat queries)
  - Validated:
    - OpenAI text-embedding-3-small sufficient for engineering domain
    - Vector search clusters topics correctly (auth ≠ frontend ≠ backend)
    - Cosine similarity returns relevant results
  - Technical debt created:
    - Embeddings stored as TEXT not VECTOR (type coercion workaround added)
    - Client-side similarity search (fetches all rows, doesn't scale)
    - No HNSW index usage (will fix in Block 3)
  - Key learning: Cache is critical (1500ms → 120ms with cache)

- [x] Block 3: MCP Integration (2025-12-16)
  - Status: PASS ✅
  - Time: 8 hours (config issues, async/sync debugging)
  - Test: End-to-end search working in Claude Desktop
  - Deliverables:
    - Modular architecture created:
      - src/kraken/config.py (52 lines) - Centralized env vars, validation
      - src/kraken/embeddings.py (87 lines) - OpenAI wrapper + persistent cache
      - src/kraken/vector_store.py (63 lines) - Supabase client-side search
      - src/kraken/mcp_server.py (200 lines) - Protocol layer, 2 tools
    - search_messages tool integrated (semantic search via Claude)
    - get_timestamp tool (health check)
  - Technical decisions:
    - **Synchronous vector_store.search()**: Supabase Python client is blocking, marking as async would be dishonest (blocks event loop anyway). Acceptable for MVP (<100ms). Fix in Block 7 with ThreadPoolExecutor if needed.
    - **Persistent embedding cache**: Reduces OpenAI calls 92% (1500ms → 120ms). Mandatory for production.
    - **Type coercion (TEXT/VECTOR)**: Supabase Python client doesn't auto-convert list → vector type. Defensive handling for both formats.
    - **Client-side similarity**: Fetches all rows, calculates in Python. Doesn't scale >10k messages. Proper fix needs pgvector RPC with HNSW index (Block 7).
  - Issues encountered:
    - MCP config: `--directory` flag doesn't set cwd correctly for .env loading. Fixed with explicit `env.PYTHONPATH` in config.
    - Async/sync mismatch: Initially marked `search()` as async but used blocking Supabase client. Fixed by making synchronous (correct pattern).
    - ModuleNotFoundError: uv environment not found by Claude Desktop. Fixed with `PYTHONPATH` in MCP config.
  - Test results:
    - Tool callable: ✅
    - Returns relevant results: ✅
    - Similarity scores: 24-49% (lower than Block 2's 84%, acceptable for diverse test data)
    - Latency: <2s ✅
    - Cache hit rate: ~95% on repeat queries ✅
  - Technical debt:
    - **Synchronous search blocks event loop** (~50-100ms per search)
      - Impact: Can't handle concurrent requests efficiently
      - Fix: ThreadPoolExecutor in Block 7
      - Priority: Low (MVP single-user, fast queries)
    - **Client-side similarity doesn't scale** (fetches all rows)
      - Impact: Breaks at >10k messages
      - Fix: Supabase RPC with pgvector HNSW index
      - Priority: Medium (blocks scaling)
    - **No proper HNSW index usage** (client-side defeats index)
      - Impact: Search is O(n) not O(log n)
      - Fix: Rewrite to use match_documents RPC
      - Priority: Medium
  - Key learnings:
    - MCP config format matters: `cwd` + `env.PYTHONPATH` required for proper module loading
    - Don't mark blocking I/O as async (defeats purpose, misleading)
    - Defensive coding pays off (type coercion handles multiple storage formats)
    - Cache is mandatory not optional (92% latency reduction)

## Now

- [ ] Block 4: Slack Integration (6-8 hours)
  - OAuth flow for workspace authorization
  - Sync service: Pull messages from Slack API
  - Pagination handling (cursor-based, 100 msgs/page)
  - Rate limiting (50 req/min Slack limit)
  - Incremental sync (only new messages since last cursor)
  - Store: content, author, channel, timestamp, permalink
  - Generate embeddings in batches (20-100 at once)
  - Insert into Supabase with deduplication (ON CONFLICT)
  - Success: 10k message channel syncs in <5 minutes
  - Prerequisites:
    - Slack workspace (free)
    - Create Slack app for OAuth
    - Bot token scopes: channels:history, channels:read, users:read

## Next

- [ ] Block 5: Multi-Customer Schemas (4-6 hours)

  - Schema-per-customer isolation (customer_acme, customer_techcorp)
  - API key → customer_id mapping (SHA-256 hashed keys)
  - Connection routing (set search_path per request)
  - Customer onboarding script (scripts/create_customer.py)
  - Test: customer_a can't see customer_b's data
  - Storage monitoring (per-customer usage tracking)
  - Supabase free tier: 500MB (8 customers), Pro: $25/month (8GB, ~130 customers)

- [ ] Block 6: Background Sync Service (3-4 hours)

  - APScheduler with SQLite job store (survives restarts)
  - Hourly sync jobs per customer
  - Fetch → Embed → Store pipeline
  - Error recovery (resume from last cursor on failure)
  - Sync lag monitoring (alert if >2 hours behind)
  - Manual sync trigger tool (for MCP server)
  - Success: Automatic hourly updates, <15 min lag

- [ ] Block 7: Production Hardening (8-10 hours)
  - Structured logging (JSON format, ELK-ready)
  - Error tracking (Sentry integration)
  - Health check endpoint (/health)
  - Metrics (Prometheus or simple logs): search latency, error rate, cache hit rate
  - Rate limiting (10 searches/min per customer)
  - Circuit breaker (stop calling failed services)
  - Graceful shutdown (finish in-flight requests)
  - Connection pooling tuning
  - Deployment automation (Railway or AWS)
  - Load testing (100 concurrent searches)
  - Chaos testing (kill Supabase, kill OpenAI, network failures)
  - Documentation: runbooks, troubleshooting, monitoring dashboards

## Technical Debt Registry

**Block 2 debt (fix in Block 3):**

- Embeddings stored as TEXT, not VECTOR type

  - Impact: JSON parsing overhead (~1ms per message)
  - Fix: Re-insert with proper CAST or fix insertion format
  - Priority: Medium (works but inefficient)

- Client-side similarity search

  - Impact: Fetches all rows (doesn't scale beyond 10k messages)
  - Fix: Use Supabase RPC with HNSW index (returns top N in 50ms)
  - Priority: High (blocks scaling)

- OpenAI API latency unpredictable (200ms-3000ms)
  - Impact: User experience varies by network/region
  - Fix: Embedding cache mitigates (120ms cached vs 1500ms uncached)
  - Priority: Low (cache solves it, API latency external)

**Future debt (post-MVP):**

- Single embedding model (OpenAI only)

  - Risk: Vendor lock-in, API outages
  - Fix: Pluggable embeddings (Cohere, Voyage, self-hosted)
  - Timeline: Month 2-3

- No real-time sync (15-60 min lag)

  - Risk: Stale data for time-sensitive queries
  - Fix: Slack Events API + websockets
  - Timeline: Month 3-4 (enterprise feature)

- Global cache (not per-customer)
  - Risk: Customer A's query cached, visible to customer B (privacy)
  - Fix: Scope cache by customer_id
  - Timeline: Block 5 (multi-customer)

## Metrics Targets

**Block 3 (MCP Integration):**

- Search latency p50: <500ms
- Search latency p95: <2s
- Cache hit rate: >80% (production usage)
- Error rate: <1% (graceful degradation)

**MVP (End of Block 7):**

- Uptime: 99.9% (43 min downtime/month allowed)
- Search relevance: >80% (manual evaluation)
- Sync lag: <60 min (hourly jobs)
- Concurrent users: 100 (load tested)
- Data volume: 100k messages/customer
- Customers: 10 beta (validate product-market fit)

## Questions to Validate

**Block 3:**

- [ ] Does proper pgvector RPC improve latency vs client-side? (Measure)
- [ ] Is 2s p95 latency acceptable for users? (User testing)
- [ ] What % of queries hit cache in production? (Metric needed)

**Block 4:**

- [ ] Can we sync 100k messages in <30 min? (Benchmark)
- [ ] Slack rate limits under load? (50 req/min, test with pagination)

**Block 5:**

- [ ] Does schema-per-customer scale to 500 customers? (Postgres limit: ~10k schemas)
- [ ] Query performance degradation with 100 schemas? (Benchmark)

**Block 7:**

- [ ] Railway vs AWS cost at 500 customers? (Railway: ~$500/month, AWS: ~$200/month)
- [ ] Self-hosting break-even point? (GPU for embeddings: ~25M embeddings/month)
