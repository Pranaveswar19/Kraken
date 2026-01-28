C:\Users\mpran\OneDrive\Desktop\Professional\Kraken\
│
├── .cache/ # Embedding cache (persistent)
│ └── embeddings.json # OpenAI embedding cache (92% latency reduction)
│
├── .venv/ # Python virtual environment (uv-managed)
│ └── (Python packages) # Isolated dependencies
│
├── src/ # Production code (import as `from kraken import ...`)
│ └── kraken/ # Main package
│ ├── **init**.py # Package marker (empty)
│ ├── config.py # Environment variable management
│ ├── embeddings.py # OpenAI API wrapper + cache
│ ├── vector_store.py # Supabase client + similarity search
│ ├── mcp_server.py # MCP protocol server (Claude Desktop)
│ └── slack_sync.py # Slack API integration (fetch/embed/store)

    sync_tracker, scheduler, retry, py.typed

│
├── scripts/ # Development/deployment tools (not imported)
│ ├── generate_test_messages.py # Creates fake Slack data (20 messages)
│ ├── insert_test_data.py # Populates Supabase with test data
│ ├── test_vector_search.py # Validates search quality
│ ├── setup_claude_config.py # Automates Claude Desktop config
│ └── sync_slack.py # CLI tool for syncing Slack channels

    run_scheduler, test_slack_connection.py

│
├── tests/ # Test data and reports
│ ├── test_messages.json # 20 fake Slack messages (4 topic clusters)
│ ├── block1-mcp-hello-world.md # Block 1 test report
│ ├── block2-vector-search-poc.md # Block 2 test report
│ └── block3-mcp-integration.md # Block 3 test report
│
├── .env # Secrets (NEVER commit)
├── .gitignore # Git exclusions
├── .python-version # Python 3.13.1 (for uv)
├── pyproject.toml # Project metadata + dependencies
├── uv.lock # Locked dependency versions
├── README.md # Project overview
├── TODO.md # Development roadmap
├── ARCHITECTURE.md # System design decisions
└── COMPONENTS.md # Technology stack explanation
