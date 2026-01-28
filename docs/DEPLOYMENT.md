# Kraken Deployment Guide

Complete setup guide for running Kraken (Slack semantic search via Claude Desktop MCP).

**Time:** 30-40 minutes  
**Cost:** ~$0.20 one-time + $0.02/month (OpenAI)

## Prerequisites

- Docker Desktop (https://www.docker.com/products/docker-desktop/)
- Slack workspace (admin access to create bot)
- Supabase account (https://supabase.com)
- OpenAI API key (https://platform.openai.com)
- Claude Desktop (https://claude.ai)

## Part 1: Database Setup (Supabase)

### 1.1 Create Project

1. Go to supabase.com and sign in
2. Click "New Project"
3. Name: kraken-search
4. Database password: Save it somewhere safe
5. Region: Choose closest to you
6. Click "Create new project" (takes 2 minutes)

### 1.2 Create Database Schema

1. Go to SQL Editor (left sidebar)
2. Click "New Query"
3. Paste this SQL and click "Run":

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE slack_messages (
    id BIGSERIAL PRIMARY KEY,
    slack_message_id TEXT UNIQUE NOT NULL,
    content TEXT NOT NULL,
    author TEXT NOT NULL,
    channel TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    thread_ts TEXT,
    permalink TEXT,
    embedding vector(1536),
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX slack_messages_embedding_idx
ON slack_messages
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

CREATE INDEX idx_channel ON slack_messages(channel);
CREATE INDEX idx_timestamp ON slack_messages(timestamp DESC);

CREATE OR REPLACE FUNCTION match_slack_messages(
    query_embedding vector(1536),
    match_threshold float DEFAULT 0.35,
    match_count int DEFAULT 5
)
RETURNS TABLE (
    id bigint,
    content text,
    author text,
    channel text,
    similarity float
)
LANGUAGE sql STABLE
AS $$
    SELECT
        id,
        content,
        author,
        channel,
        1 - (embedding <=> query_embedding) AS similarity
    FROM slack_messages
    WHERE 1 - (embedding <=> query_embedding) > match_threshold
    ORDER BY embedding <=> query_embedding
    LIMIT match_count;
$$;
```

### 1.3 Get API Credentials

1. Go to Settings → API
2. Copy and save these:
   - Project URL: https://xxxxx.supabase.co
   - Service Role Key: Click "Reveal" then copy

## Part 2: Slack Bot Setup

### 2.1 Create Slack App

1. Go to api.slack.com/apps
2. Click "Create New App" → "From scratch"
3. App Name: Kraken Search Bot
4. Workspace: Choose your workspace
5. Click "Create App"

### 2.2 Add Permissions

1. Left sidebar: OAuth & Permissions
2. Scroll to Bot Token Scopes
3. Click "Add an OAuth Scope" and add:
   - channels:history
   - channels:read
   - users:read

### 2.3 Install Bot

1. Scroll to top → Click "Install to Workspace"
2. Review permissions → Click "Allow"
3. Copy Bot User OAuth Token (starts with xoxb-)

### 2.4 Invite Bot to Channel

1. Go to Slack
2. Open the channel you want to search
3. Type: /invite @Kraken Search Bot

### 2.5 Get Channel ID

Right-click channel name → View channel details → Copy Channel ID

Or from URL: https://app.slack.com/client/T.../C0A474TT6CU
Channel ID is the part starting with C

## Part 3: OpenAI API Key

1. Go to platform.openai.com/api-keys
2. Sign in
3. Click "Create new secret key"
4. Name: kraken-embeddings
5. Copy the key (starts with sk-proj-)

## Part 4: Project Setup

### 4.1 Clone Repository

```bash
git clone https://github.com/YOUR_USERNAME/kraken.git
cd kraken
```

### 4.2 Create .env File

Create .env in project root:

```
OPENAI_API_KEY=sk-proj-YOUR_KEY_HERE
SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_SERVICE_KEY=YOUR_SERVICE_ROLE_KEY_HERE
SLACK_BOT_TOKEN=xoxb-YOUR_BOT_TOKEN_HERE
SYNC_CHANNELS=C0A474TT6CU
SYNC_INTERVAL_HOURS=60
```

Replace all placeholders with your actual credentials.

For multiple channels: SYNC_CHANNELS=C0A474TT6CU,C1B2A3C4D5

## Part 5: Initial Sync

Sync existing messages (one-time):

```bash
python scripts/sync_slack.py --channel C0A474TT6CU --limit 1000
```

Expected: 5-10 minutes for 1000 messages

Verify in Supabase:

1. Table Editor → slack_messages
2. Should see your messages

## Part 6: Start Background Sync (Docker)

### 6.1 Build & Run

```bash
docker-compose build
docker-compose up -d
```

### 6.2 Verify Running

```bash
docker-compose logs -f
```

Should see:

- Sync interval: 1 hours
- [OK] Scheduled sync for channel C0A474TT6CU
- Scheduler is running

Press Ctrl+C to exit logs (scheduler keeps running)

### 6.3 Manage Scheduler

```bash
docker-compose down
docker-compose restart
docker-compose logs -f scheduler
```

## Part 7: Claude Desktop Integration (MCP)

### 7.1 Configure Claude Desktop

Windows: Open %APPDATA%\Claude\claude_desktop_config.json

Add this configuration:

```json
{
  "mcpServers": {
    "kraken": {
      "command": "uv",
      "args": [
        "--directory",
        "C:/Users/YourName/path/to/kraken",
        "run",
        "python",
        "-m",
        "kraken.mcp_server"
      ]
    }
  }
}
```

Update the path with your actual project location.
Use forward slashes (/)

Mac/Linux:

```json
{
  "mcpServers": {
    "kraken": {
      "command": "uv",
      "args": [
        "--directory",
        "/Users/yourname/kraken",
        "run",
        "python",
        "-m",
        "kraken.mcp_server"
      ]
    }
  }
}
```

### 7.2 Restart Claude Desktop

Quit Claude Desktop completely, wait 5 seconds, reopen.

### 7.3 Test Search

In Claude, ask: "Search my Slack messages for authentication bugs"

If you see results, setup is complete.

## Troubleshooting

### Scheduler not syncing

Check logs:

```bash
docker-compose logs scheduler
```

Common issues:

- Wrong Slack token: Verify SLACK_BOT_TOKEN in .env
- Bot not in channel: /invite @Kraken Search Bot
- Wrong channel ID: Verify SYNC_CHANNELS in .env

### MCP search not working

Check Claude logs:
Windows: %APPDATA%\Claude\logs\mcp-server-kraken\*.log

Common issues:

- Path wrong in config: Update claude_desktop_config.json
- Config not loaded: Restart Claude Desktop
- No results: Run initial sync (Part 5)

### No search results

1. Verify database has data in Supabase Table Editor
2. Lower threshold in .env: MIN_SIMILARITY_THRESHOLD=0.25
3. Re-run initial sync

## Costs

- Supabase: Free tier (500MB, ~10k messages)
- OpenAI: $0.02 per 1000 messages
- Docker: Free

Total: ~$0.20 setup + $0.02/month

## Updating

```bash
cd kraken
git pull origin main
docker-compose down
docker-compose build
docker-compose up -d
```

## Uninstall

```bash
docker-compose down
rm -rf .cache/
rm jobs.sqlite
```

Delete project from Supabase dashboard.

## Security Notes

- .env is gitignored (secrets never committed)
- Never share Service Role Key or Bot Token
- Never commit .env to git

## Support

Issues: https://github.com/YOUR_USERNAME/kraken/issues
