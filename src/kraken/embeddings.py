import json
import hashlib
import time
from pathlib import Path
from typing import Optional, Tuple, List
from openai import OpenAI, OpenAIError

from kraken.config import config


class EmbeddingCache:
    def __init__(self, cache_file: Path):
        self.cache_file = cache_file
        self.cache: dict = {}
        self.hits = 0
        self.misses = 0
        self._load()
    
    def _load(self):
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r') as f:
                    self.cache = json.load(f)
            except Exception:
                self.cache = {}
        else:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
    
    def _save(self):
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self.cache, f)
        except Exception:
            pass
    
    def _key(self, text: str, model: str) -> str:
        return hashlib.sha256(f"{model}:{text}".encode()).hexdigest()
    
    def get(self, text: str, model: str) -> Optional[List[float]]:
        key = self._key(text, model)
        if key in self.cache:
            self.hits += 1
            return self.cache[key]["embedding"]
        self.misses += 1
        return None
    
    def set(self, text: str, model: str, embedding: List[float]):
        key = self._key(text, model)
        self.cache[key] = {
            "text": text,
            "embedding": embedding,
            "model": model,
            "timestamp": int(time.time())
        }
        self._save()


_cache = EmbeddingCache(config.CACHE_DIR / "embeddings.json") if config.EMBEDDING_CACHE_ENABLED else None


async def generate_embedding(text: str, model: Optional[str] = None) -> Tuple[List[float], float, bool]:
    start = time.time()
    model = model or config.OPENAI_EMBEDDING_MODEL
    
    if _cache:
        cached = _cache.get(text, model)
        if cached:
            latency = (time.time() - start) * 1000
            return cached, latency, True
    
    try:
        client = OpenAI(api_key=config.OPENAI_API_KEY)
        response = client.embeddings.create(model=model, input=text)
        embedding = response.data[0].embedding
        
        if _cache:
            _cache.set(text, model, embedding)
        
        latency = (time.time() - start) * 1000
        return embedding, latency, False
    except OpenAIError as e:
        print(f"OpenAI API error: {e}")
        raise
