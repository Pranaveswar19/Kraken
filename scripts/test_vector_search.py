import os
import time
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Optional
from dotenv import load_dotenv
from openai import OpenAI
from supabase import create_client, Client
import numpy as np

load_dotenv()

openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_KEY")
)

CACHE_DIR = Path(__file__).parent.parent / ".cache"
CACHE_FILE = CACHE_DIR / "embeddings_cache.json"

TEST_QUERIES = [
    {
        "query": "authentication bug",
        "expected_topic": "auth/security",
        "expected_authors": ["Sarah Chen", "Mike Rodriguez", "Alex Kim"]
    },
    {
        "query": "database migration",
        "expected_topic": "database/backend",
        "expected_authors": ["Mike Rodriguez", "Alex Kim"]
    },
    {
        "query": "button not working on mobile",
        "expected_topic": "frontend/UI",
        "expected_authors": ["Emma Wilson", "Jordan Lee"]
    },
    {
        "query": "deployment to production",
        "expected_topic": "devops/infrastructure",
        "expected_authors": ["Alex Kim", "Chris Taylor"]
    },
    {
        "query": "API performance issues",
        "expected_topic": "backend/performance",
        "expected_authors": ["Mike Rodriguez", "Alex Kim"]
    }
]


class EmbeddingCache:
    def __init__(self, cache_file: Path):
        self.cache_file = cache_file
        self.cache: Dict = {}
        self.hits = 0
        self.misses = 0
        self._load()
    
    def _load(self):
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r') as f:
                    self.cache = json.load(f)
                print(f"Loaded {len(self.cache)} cached embeddings")
            except Exception as e:
                print(f"Cache load failed: {e}, starting fresh")
                self.cache = {}
        else:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
    
    def _save(self):
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self.cache, f, indent=2)
        except Exception as e:
            print(f"Cache save failed: {e}")
    
    def _hash_query(self, query: str, model: str) -> str:
        key = f"{model}:{query}"
        return hashlib.sha256(key.encode()).hexdigest()
    
    def get(self, query: str, model: str = "text-embedding-3-small") -> Optional[List[float]]:
        key = self._hash_query(query, model)
        
        if key in self.cache:
            self.hits += 1
            return self.cache[key]["embedding"]
        
        self.misses += 1
        return None
    
    def set(self, query: str, embedding: List[float], model: str = "text-embedding-3-small"):
        key = self._hash_query(query, model)
        
        self.cache[key] = {
            "query": query,
            "embedding": embedding,
            "timestamp": int(time.time()),
            "model": model
        }
        
        self._save()
    
    def stats(self) -> Dict:
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0
        
        return {
            "size": len(self.cache),
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": hit_rate
        }


embedding_cache = EmbeddingCache(CACHE_FILE)


def generate_query_embedding(query: str) -> tuple[List[float], float, bool]:
    start = time.time()
    
    cached = embedding_cache.get(query)
    if cached is not None:
        latency = (time.time() - start) * 1000
        return cached, latency, True
    
    try:
        response = openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=query
        )
        embedding = response.data[0].embedding
        
        embedding_cache.set(query, embedding)
        
        latency = (time.time() - start) * 1000
        return embedding, latency, False
        
    except Exception as e:
        print(f"OpenAI API error: {e}")
        raise


def search_messages(query_embedding: List[float], limit: int = 5) -> tuple[List[Dict], float]:
    start = time.time()
    
    try:
        all_messages = supabase.table("test_messages").select("*").execute()
        
        if not all_messages.data:
            return [], 0.0
        
        query_vec = np.array(query_embedding, dtype=np.float64)
        results = []
        
        for msg in all_messages.data:
            embedding_raw = msg.get("embedding")
            if not embedding_raw:
                continue
            
            if isinstance(embedding_raw, str):
                try:
                    import json
                    embedding_list = json.loads(embedding_raw)
                except json.JSONDecodeError:
                    print(f"Warning: Could not parse embedding for message {msg.get('id')}")
                    continue
            elif isinstance(embedding_raw, list):
                embedding_list = embedding_raw
            else:
                print(f"Warning: Unknown embedding type {type(embedding_raw)}")
                continue
            
            msg_vec = np.array(embedding_list, dtype=np.float64)
            
            if len(msg_vec) != len(query_vec):
                print(f"Warning: Dimension mismatch: {len(msg_vec)} vs {len(query_vec)}")
                continue
            
            try:
                similarity = float(
                    np.dot(query_vec, msg_vec) / (
                        np.linalg.norm(query_vec) * np.linalg.norm(msg_vec)
                    )
                )
            except Exception as e:
                print(f"Warning: Similarity calculation failed: {e}")
                continue
            
            results.append({
                "id": msg["id"],
                "content": msg["content"],
                "author": msg["author"],
                "channel": msg["channel"],
                "similarity": similarity
            })
        
        results.sort(key=lambda x: x["similarity"], reverse=True)
        
        latency = (time.time() - start) * 1000
        return results[:limit], latency
        
    except Exception as e:
        print(f"Search error: {e}")
        import traceback
        traceback.print_exc()
        raise


def evaluate_relevance(query_info: Dict, results: List[Dict]) -> Dict:
    query = query_info["query"]
    expected_topic = query_info["expected_topic"]
    expected_authors = query_info["expected_authors"]
    
    print(f"\nQuery: '{query}'")
    print(f"Expected topic: {expected_topic}")
    print(f"Expected authors: {', '.join(expected_authors)}")
    print("-" * 60)
    
    if not results:
        print("No results returned!")
        return {
            "relevant_count": 0,
            "total_count": 0,
            "relevance_pct": 0.0
        }
    
    relevant_count = 0
    
    for i, result in enumerate(results, 1):
        author = result["author"]
        content = result["content"]
        similarity = result["similarity"]
        
        is_relevant = author in expected_authors
        relevant_count += is_relevant
        
        marker = "✓" if is_relevant else "✗"
        
        print(f"{i}. [{marker}] {author} (similarity: {similarity:.3f})")
        print(f"   {content[:80]}...")
        print()
    
    relevance_pct = (relevant_count / len(results)) * 100
    print(f"Relevance: {relevant_count}/{len(results)} ({relevance_pct:.0f}%)")
    
    return {
        "relevant_count": relevant_count,
        "total_count": len(results),
        "relevance_pct": relevance_pct
    }


def run_search_test(query_info: Dict, run_number: int) -> Dict:
    query = query_info["query"]
    
    print(f"\n[Run #{run_number}]")
    
    total_start = time.time()
    
    embedding, embedding_latency, cache_hit = generate_query_embedding(query)
    cache_status = "CACHE HIT" if cache_hit else "CACHE MISS (OpenAI call)"
    
    results, search_latency = search_messages(embedding, limit=5)
    
    total_latency = (time.time() - total_start) * 1000
    
    evaluation = evaluate_relevance(query_info, results)
    
    print(f"\nTiming:")
    print(f"  Embedding: {embedding_latency:.0f}ms ({cache_status})")
    print(f"  Search: {search_latency:.0f}ms")
    print(f"  Total: {total_latency:.0f}ms")
    
    return {
        "query": query,
        "results": results,
        "evaluation": evaluation,
        "latency_ms": total_latency,
        "embedding_latency_ms": embedding_latency,
        "search_latency_ms": search_latency,
        "cache_hit": cache_hit
    }


def main():
    print("=" * 60)
    print("Vector Search Testing (Optimized with Cache)")
    print("=" * 60)
    print()
    
    print("PASS 1: Cold Cache (OpenAI API calls)")
    print("=" * 60)
    
    pass1_results = []
    for query_info in TEST_QUERIES:
        result = run_search_test(query_info, run_number=1)
        pass1_results.append(result)
        print("=" * 60)
    
    print("\n\nPASS 2: Warm Cache (Cached embeddings)")
    print("=" * 60)
    
    pass2_results = []
    for query_info in TEST_QUERIES:
        result = run_search_test(query_info, run_number=2)
        pass2_results.append(result)
        print("=" * 60)
    
    for pass_num, results in [(1, pass1_results), (2, pass2_results)]:
        print(f"\n{'=' * 60}")
        print(f"SUMMARY - PASS {pass_num}")
        print("=" * 60)
        print()
        
        total_relevant = sum(r["evaluation"]["relevant_count"] for r in results)
        total_results = sum(r["evaluation"]["total_count"] for r in results)
        overall_relevance = (total_relevant / total_results * 100) if total_results > 0 else 0
        
        print(f"Overall Relevance: {total_relevant}/{total_results} ({overall_relevance:.0f}%)")
        print()
        
        latencies = [r["latency_ms"] for r in results]
        avg_latency = sum(latencies) / len(latencies)
        max_latency = max(latencies)
        min_latency = min(latencies)
        
        embedding_latencies = [r["embedding_latency_ms"] for r in results]
        avg_embedding = sum(embedding_latencies) / len(embedding_latencies)
        
        search_latencies = [r["search_latency_ms"] for r in results]
        avg_search = sum(search_latencies) / len(search_latencies)
        
        print(f"Latency:")
        print(f"  Average Total: {avg_latency:.0f}ms")
        print(f"  Average Embedding: {avg_embedding:.0f}ms")
        print(f"  Average Search: {avg_search:.0f}ms")
        print(f"  Min: {min_latency:.0f}ms")
        print(f"  Max: {max_latency:.0f}ms")
        print()
        
        cache_hits = sum(1 for r in results if r["cache_hit"])
        cache_misses = sum(1 for r in results if not r["cache_hit"])
        print(f"Cache Performance:")
        print(f"  Hits: {cache_hits}")
        print(f"  Misses: {cache_misses}")
        print()
        
        print("Per-query results:")
        for r in results:
            relevance_pct = r["evaluation"]["relevance_pct"]
            cache_marker = "⚡" if r["cache_hit"] else "🌐"
            status = "✓ PASS" if relevance_pct >= 60 else "✗ FAIL"
            print(f"  {cache_marker} {r['query'][:30]:30} | {relevance_pct:3.0f}% | {r['latency_ms']:4.0f}ms | {status}")
        print()
        
        print("Success Criteria:")
        
        relevance_pass = overall_relevance >= 80
        print(f"  Relevance ≥80%: {overall_relevance:.0f}% ... {'✓ PASS' if relevance_pass else '✗ FAIL'}")
        
        latency_target = 500 if pass_num == 1 else 200
        latency_pass = avg_latency < latency_target
        print(f"  Latency <{latency_target}ms: {avg_latency:.0f}ms ... {'✓ PASS' if latency_pass else '✗ FAIL'}")
        print()
        
        if pass_num == 2:
            if relevance_pass and latency_pass:
                print("=" * 60)
                print("✓ Block 2 PASS: Vector search validated")
                print("=" * 60)
                print()
                print("Key findings:")
                print(f"  - Relevance: {overall_relevance:.0f}% (production-ready)")
                print(f"  - Cached latency: {avg_latency:.0f}ms (excellent)")
                print(f"  - Cache hit rate: {cache_hits}/5 (100% on second pass)")
                print()
                print("Next steps:")
                print("  1. Document results in tests/block2-vector-search-poc.md")
                print("  2. Commit to git")
                print("  3. Block 3: Integrate into MCP server with caching")
            else:
                print("=" * 60)
                print("✗ Block 2 CONDITIONAL: Needs optimization")
                print("=" * 60)
                print()
                if not relevance_pass:
                    print("Issues:")
                    print("  - Relevance too low, consider different embedding model")
                if not latency_pass:
                    print("Issues:")
                    print(f"  - Pass 2 still slow ({avg_latency:.0f}ms)")
                    print("  - Check: OpenAI API region (try different endpoint)")
                    print("  - Check: Network connection (VPN, proxy?)")
    
    print(f"\n{'=' * 60}")
    print("OVERALL CACHE STATISTICS")
    print("=" * 60)
    cache_stats = embedding_cache.stats()
    print(f"Cache size: {cache_stats['size']} embeddings")
    print(f"Total hits: {cache_stats['hits']}")
    print(f"Total misses: {cache_stats['misses']}")
    print(f"Hit rate: {cache_stats['hit_rate']:.1f}%")
    print(f"Cache location: {CACHE_FILE}")


if __name__ == "__main__":
    main()
