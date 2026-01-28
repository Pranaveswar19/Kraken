import json
from typing import List, Dict, Optional
import numpy as np
from supabase import create_client, Client

from kraken.config import config
from kraken.retry import with_retry


class VectorStore:
    def __init__(self, table_name: str = "slack_messages"):
        self.client: Client = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
        self.table_name = table_name

    def search(
        self,
        query_embedding: List[float],
        limit: int = 5,
        min_similarity: float = 0.35,
        table_name: Optional[str] = None
    ) -> List[Dict]:
        """Search for similar messages using pgvector RPC (server-side)."""
        table = table_name or self.table_name

        result = with_retry(
            lambda: self.client.rpc(
                'match_slack_messages',
                {
                    'query_embedding': query_embedding,
                    'match_threshold': min_similarity,
                    'match_count': limit
                }
            ).execute(),
            max_retries=3,
            operation_name="Supabase match_slack_messages RPC"
        )

        return result.data


vector_store = VectorStore()

if __name__ == "__main__":
    from kraken.embeddings import generate_embedding
    import asyncio

    async def test():
        store = VectorStore(table_name="slack_messages")
        query = "authentication bug"
        embedding, _, _ = await generate_embedding(query)
        results = store.search(embedding, limit=3)

        print(f"Query: {query}")
        print(f"Results: {len(results)}")
        for i, r in enumerate(results, 1):
            print(f"{i}. [{r['author']}] {r['content'][:60]}... (similarity: {r['similarity']:.2f})")

    asyncio.run(test())
