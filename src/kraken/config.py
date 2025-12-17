import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


class Config:
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_EMBEDDING_MODEL: str = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_SERVICE_KEY: str = os.getenv("SUPABASE_SERVICE_KEY", "")
    
    CACHE_DIR: Path = Path(os.getenv("CACHE_DIR", ".cache"))
    EMBEDDING_CACHE_ENABLED: bool = os.getenv("EMBEDDING_CACHE_ENABLED", "true").lower() == "true"
    
    DEFAULT_SEARCH_LIMIT: int = int(os.getenv("DEFAULT_SEARCH_LIMIT", "5"))
    MIN_SIMILARITY_THRESHOLD: float = float(os.getenv("MIN_SIMILARITY_THRESHOLD", "0.0"))
    
    def validate(self) -> None:
        errors = []
        
        if not self.OPENAI_API_KEY:
            errors.append("OPENAI_API_KEY not set")
        if not self.SUPABASE_URL:
            errors.append("SUPABASE_URL not set")
        if not self.SUPABASE_SERVICE_KEY:
            errors.append("SUPABASE_SERVICE_KEY not set")
        
        if errors:
            raise ValueError("Missing required configuration:\n" + "\n".join(f"  - {e}" for e in errors))


config = Config()

try:
    config.validate()
except ValueError as e:
    print(f"Configuration error: {e}")
    print("\nSet these in .env file:")
    print("  OPENAI_API_KEY=sk-proj-...")
    print("  SUPABASE_URL=https://xxx.supabase.co")
    print("  SUPABASE_SERVICE_KEY=...")
    raise
