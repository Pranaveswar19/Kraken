import json
from typing import List, Dict
import numpy as np
from supabase import create_client, Client

from kraken.config import config


class VectorStore:
    def __init__(self):
        self.client: Client = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
    
    def search(self, query_embedding: List[float], limit: int = 5, min_similarity: float = 0.0) -> List[Dict]:
        response = self.client.table("test_messages").select("*").execute()
        
        if not response.data:
            return []
        
        query_vec = np.array(query_embedding, dtype=np.float64)
        results = []
        
        for msg in response.data:
            embedding_raw = msg.get("embedding")
            if not embedding_raw:
                continue
            
            if isinstance(embedding_raw, str):
                try:
                    embedding_list = json.loads(embedding_raw)
                except json.JSONDecodeError:
                    continue
            else:
                embedding_list = embedding_raw
            
            msg_vec = np.array(embedding_list, dtype=np.float64)
            
            similarity = float(np.dot(query_vec, msg_vec) / (np.linalg.norm(query_vec) * np.linalg.norm(msg_vec)))
            
            if similarity >= min_similarity:
                results.append({
                    "id": msg["id"],
                    "content": msg["content"],
                    "author": msg["author"],
                    "channel": msg["channel"],
                    "similarity": similarity
                })
        
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:limit]


vector_store = VectorStore()
