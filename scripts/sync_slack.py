"""
Slack sync CLI tool.

Usage:
    python scripts/sync_slack.py --channel C0A474TT6CU
    python scripts/sync_slack.py --channel C0A474TT6CU --limit 100
    python scripts/sync_slack.py --channel C0A474TT6CU --dry-run

Why this file exists:
    src/kraken/slack_sync.py = library (reusable functions)
    scripts/sync_slack.py = CLI (user interface to call library)
    
Separation of concerns: business logic vs user interface.
"""

import argparse  # Standard library for parsing command-line arguments
import os
import time
from dotenv import load_dotenv
from kraken.slack_sync import SlackSyncService

# Load .env file (SLACK_BOT_TOKEN, etc.)
load_dotenv()


def sync_channel(channel_id: str, limit: int, dry_run: bool) -> None:
    """
    Sync a Slack channel to Supabase.
    
    Args:
        channel_id: Slack channel ID (e.g., C0A474TT6CU)
        limit: Max messages to fetch (pagination stops at this)
        dry_run: If True, fetch and process but don't insert to DB
        
    Returns:
        None (prints progress to stdout)
        
    Why separate function:
        - Testable (can call from tests without argparse)
        - Reusable (other scripts can import this)
        - Clear responsibilities (argparse handles CLI, this handles logic)
    """
    
    # Start timer (for summary stats)
    start_time = time.time()
    
    print(f"Starting sync for channel {channel_id}...")
    print(f"Limit: {limit} messages")
    if dry_run:
        print("[DRY RUN MODE] No data will be inserted")
    print()
    
    # Initialize service
    token = os.getenv("SLACK_BOT_TOKEN")
    if not token:
        # Fail fast with clear error message
        print("❌ Error: SLACK_BOT_TOKEN not found in .env")
        print("   Add: SLACK_BOT_TOKEN=xoxb-your-token")
        return
    
    service = SlackSyncService(token)
    
    # Phase 1: Fetch messages with pagination
    print("Phase 1: Fetching messages from Slack...")
    all_messages = []
    cursor = None
    
    while True:
        # Fetch one page
        messages, cursor = service.fetch_messages(
            channel_id, 
            cursor=cursor,
            limit=100  # Slack max per page
        )
        all_messages.extend(messages)
        
        # Progress feedback (every page)
        print(f"  Fetched {len(all_messages)} messages so far...")
        
        # Stop conditions
        if not cursor:  # No more pages
            break
        if len(all_messages) >= limit:  # Hit user's limit
            all_messages = all_messages[:limit]  # Trim to exact limit
            break
    
    print(f"✓ Fetched {len(all_messages)} total messages")
    print()
    
    # Phase 2: Enrich (user IDs → names, filter system messages)
    print("Phase 2: Enriching messages...")
    enriched = service.enrich_messages(all_messages, channel_id)
    print(f"✓ {len(enriched)} user messages (filtered {len(all_messages) - len(enriched)} system messages)")
    print()
    
    if len(enriched) == 0:
        print("⚠ No user messages found. Channel might be empty or only have system messages.")
        return
    
    # Phase 3: Generate embeddings
    print("Phase 3: Generating embeddings...")
    embeddings = service.batch_embed(enriched)
    
    # Cost estimation
    # OpenAI pricing: $0.02 per 1M tokens
    # Rough estimate: 50 tokens per message (actual varies, but ballpark)
    estimated_tokens = len(enriched) * 50
    estimated_cost = (estimated_tokens / 1_000_000) * 0.02
    
    print(f"✓ Generated {len(embeddings)} embeddings")
    print(f"  Estimated tokens: {estimated_tokens:,}")
    print(f"  Estimated cost: ${estimated_cost:.4f}")
    print()
    
    # Phase 4: Insert to database
    if dry_run:
        print("Phase 4: [DRY RUN] Skipping database insert")
        print(f"  Would insert {len(enriched)} messages")
    else:
        print("Phase 4: Inserting to Supabase...")
        count = service.upsert_to_db(enriched, embeddings)
        print(f"✓ Inserted {count} messages")
    
    print()
    
    # Summary
    duration = time.time() - start_time
    print("=" * 50)
    print("Summary:")
    print(f"  Channel: {channel_id}")
    print(f"  Messages fetched: {len(all_messages)}")
    print(f"  User messages: {len(enriched)}")
    print(f"  Embeddings generated: {len(embeddings)}")
    if not dry_run:
        print(f"  Inserted to DB: {count}")
    print(f"  Time: {duration:.1f}s")
    print(f"  Cost: ${estimated_cost:.4f}")
    print("=" * 50)


def main() -> None:
    """
    Entry point for CLI.
    
    Why separate from sync_channel():
        - main() handles argparse (CLI concerns)
        - sync_channel() handles business logic
        - Can call sync_channel() from other code without argparse
    """
    
    # Create argument parser
    # description shows up in --help
    parser = argparse.ArgumentParser(
        description='Sync Slack channel messages to Supabase vector database',
        formatter_class=argparse.RawDescriptionHelpFormatter,  # Preserve formatting
        epilog="""
Examples:
  # Sync specific channel
  python scripts/sync_slack.py --channel C0A474TT6CU
  
  # Limit to first 100 messages
  python scripts/sync_slack.py --channel C0A474TT6CU --limit 100
  
  # Dry run (preview without inserting)
  python scripts/sync_slack.py --channel C0A474TT6CU --dry-run
        """
    )
    
    # Define arguments
    parser.add_argument(
        '--channel',
        required=True,  # Must provide this
        help='Slack channel ID (e.g., C0A474TT6CU). Find it in channel details or URL.'
    )
    
    parser.add_argument(
        '--limit',
        type=int,  # Convert string to integer
        default=1000,  # If not provided, use 1000
        help='Maximum messages to sync (default: 1000)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',  # Flag (no value needed, presence = True)
        help='Fetch and process but do not insert to database'
    )
    
    # Parse arguments
    args = parser.parse_args()
    
    # Call main logic
    sync_channel(
        channel_id=args.channel,
        limit=args.limit,
        dry_run=args.dry_run
    )


# Python convention: only run main() if script is executed directly
# If imported from another file, this block is skipped
if __name__ == "__main__":
    main()
