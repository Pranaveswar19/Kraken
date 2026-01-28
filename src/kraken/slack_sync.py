"""Slack integration with batch user enrichment and retry logic."""

import logging
from typing import List, Dict, Tuple, Optional
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from kraken.retry import with_retry

logger = logging.getLogger(__name__)


class SlackSyncService:
    """Slack message fetching, enrichment, embedding, and storage."""

    def __init__(self, slack_token: str):
        """Initialize Slack client."""
        self.client = WebClient(token=slack_token)
        self._user_cache: Optional[Dict[str, str]] = None
    
    def _get_user_map(self) -> Dict[str, str]:
        """Fetch all workspace users once, cache in memory. Maps user_id -> real_name."""
        if self._user_cache is not None:
            return self._user_cache

        try:
            response = with_retry(
                lambda: self.client.users_list(),
                max_retries=3,
                operation_name="Slack users.list"
            )

            self._user_cache = {
                user['id']: user.get('real_name') or user.get('name', user['id'])
                for user in response['members']
                if not user.get('deleted', False)
            }

            print(f"Cached {len(self._user_cache)} users")
            return self._user_cache

        except Exception as e:
            print(f"Warning: Failed to fetch user list after retries: {e}")
            return {}
    
    def fetch_messages(
        self,
        channel_id: str,
        oldest: Optional[str] = None,
        cursor: Optional[str] = None,
        limit: int = 100
    ) -> Tuple[List[Dict], Optional[str]]:
        """Fetch messages from Slack channel with retry on transient failures."""
        response = with_retry(
            lambda: self.client.conversations_history(
                channel=channel_id,
                oldest=oldest,
                cursor=cursor,
                limit=limit
            ),
            max_retries=3,
            operation_name=f"Slack conversations.history (channel={channel_id})"
        )

        messages = response.get('messages', [])
        next_cursor = response.get('response_metadata', {}).get('next_cursor')

        return messages, next_cursor
    
    def enrich_messages(self, messages: List[Dict], channel_id: str) -> List[Dict]:
        """Enrich messages with user names and metadata."""
        user_map = self._get_user_map()
        enriched = []

        for msg in messages:
            if msg.get('subtype'):
                continue

            if not msg.get('text'):
                continue

            user_id = msg.get('user', 'unknown')
            author = user_map.get(user_id, user_id)

            timestamp = msg.get('ts', '0')
            permalink = f"https://slack.com/archives/{channel_id}/p{timestamp.replace('.', '')}"

            enriched.append({
                'slack_message_id': f"{channel_id}_{timestamp}",
                'content': msg['text'],
                'author': author,
                'channel': channel_id,
                'timestamp': timestamp,
                'thread_ts': msg.get('thread_ts'),
                'permalink': permalink,
                'metadata': {
                    'type': msg.get('type', 'message'),
                    'user_id': user_id
                }
            })

        return enriched
    
    def batch_embed(self, messages: List[Dict]) -> List[List[float]]:
        """Generate embeddings for messages in batch."""
        from openai import OpenAI
        from kraken.config import config

        client = OpenAI(api_key=config.OPENAI_API_KEY)
        texts = [msg['content'] for msg in messages]

        response = with_retry(
            lambda: client.embeddings.create(
                model=config.OPENAI_EMBEDDING_MODEL,
                input=texts
            ),
            max_retries=3,
            operation_name="OpenAI embeddings.create"
        )

        embeddings = [item.embedding for item in response.data]
        return embeddings
    
    def upsert_to_db(self, messages: List[Dict], embeddings: List[List[float]]) -> int:
        """Insert messages with embeddings into Supabase (idempotent upsert)."""
        from supabase import create_client
        from kraken.config import config
        from datetime import datetime

        client = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)

        rows = []
        for msg, embedding in zip(messages, embeddings):
            slack_ts = float(msg['timestamp'])
            pg_timestamp = datetime.fromtimestamp(slack_ts).isoformat()

            rows.append({
                'slack_message_id': msg['slack_message_id'],
                'content': msg['content'],
                'author': msg['author'],
                'channel': msg['channel'],
                'timestamp': pg_timestamp,
                'thread_ts': msg.get('thread_ts'),
                'permalink': msg.get('permalink'),
                'embedding': embedding,
                'metadata': msg.get('metadata', {})
            })

        result = with_retry(
            lambda: client.table('slack_messages').upsert(
                rows,
                on_conflict='slack_message_id'
            ).execute(),
            max_retries=3,
            operation_name="Supabase slack_messages.upsert"
        )

        return len(result.data)
