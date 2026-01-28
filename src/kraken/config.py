"""Configuration management for Kraken."""

import os
from pathlib import Path
from typing import List
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration with validation."""

    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_EMBEDDING_MODEL: str = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_SERVICE_KEY: str = os.getenv("SUPABASE_SERVICE_KEY", "")
    SLACK_BOT_TOKEN: str = os.getenv("SLACK_BOT_TOKEN", "")
    SYNC_CHANNELS: str = os.getenv("SYNC_CHANNELS", "")
    SYNC_INTERVAL_HOURS: int = int(os.getenv("SYNC_INTERVAL_HOURS", "60"))
    CACHE_DIR: Path = Path(os.getenv("CACHE_DIR", ".cache"))
    EMBEDDING_CACHE_ENABLED: bool = os.getenv("EMBEDDING_CACHE_ENABLED", "true").lower() == "true"
    DEFAULT_SEARCH_LIMIT: int = int(os.getenv("DEFAULT_SEARCH_LIMIT", "5"))
    MIN_SIMILARITY_THRESHOLD: float = float(os.getenv("MIN_SIMILARITY_THRESHOLD", "0.35"))
    
    @property
    def sync_channels_list(self) -> List[str]:
        """Parse comma-separated channel IDs into list."""
        if not self.SYNC_CHANNELS:
            return []
        return [ch.strip() for ch in self.SYNC_CHANNELS.split(',') if ch.strip()]
    
    @property
    def sync_interval_minutes(self) -> int:
        """Get sync interval in minutes."""
        return self.SYNC_INTERVAL_HOURS
    
    def validate(self) -> None:
        """Validate required configuration."""
        errors = []
        
        if not self.OPENAI_API_KEY:
            errors.append("OPENAI_API_KEY not set")
        if not self.SUPABASE_URL:
            errors.append("SUPABASE_URL not set")
        if not self.SUPABASE_SERVICE_KEY:
            errors.append("SUPABASE_SERVICE_KEY not set")
        if not self.SLACK_BOT_TOKEN:
            errors.append("SLACK_BOT_TOKEN not set")
        
        if errors:
            raise ValueError("Missing required configuration:\n" + "\n".join(f"  - {e}" for e in errors))
    
    def validate_sync_config(self) -> None:
        """Validate sync-specific configuration."""
        if not self.SYNC_CHANNELS:
            raise ValueError(
                "SYNC_CHANNELS not set.\n"
                "Add to .env file: SYNC_CHANNELS=C0A474TT6CU,C1B2A3C4D5"
            )
        
        channels = self.sync_channels_list
        if not channels:
            raise ValueError(
                "SYNC_CHANNELS is empty or invalid.\n"
                "Format: SYNC_CHANNELS=C0A474TT6CU,C1B2A3C4D5"
            )
        
        for ch in channels:
            if not ch.startswith('C') or len(ch) != 11:
                raise ValueError(
                    f"Invalid channel ID format: {ch}\n"
                    f"Slack channel IDs should start with 'C' and be 11 characters.\n"
                    f"Example: C0A474TT6CU"
                )
        
        interval_min = self.sync_interval_minutes
        
        if interval_min < 1:
            raise ValueError(
                f"Invalid SYNC_INTERVAL_HOURS: {interval_min}\n"
                f"Must be at least 1 minute"
            )
        
        if interval_min > 1440:  # 24 hours
            raise ValueError(
                f"Invalid SYNC_INTERVAL_HOURS: {interval_min} minutes\n"
                f"Maximum is 1440 minutes (24 hours)"
            )
        
        if interval_min < 5:
            import logging
            logging.getLogger(__name__).warning(
                f"⚠️  Sync interval is very frequent: {interval_min} minutes. "
                f"This may hit Slack rate limits (50 req/min). "
                f"Recommended: 5+ minutes for testing, 60 minutes for production."
            )


config = Config()

try:
    config.validate()
except ValueError as e:
    print(f"Configuration error: {e}")
    print("\nSet these in .env file:")
    print("  OPENAI_API_KEY=sk-proj-...")
    print("  SUPABASE_URL=https://xxx.supabase.co")
    print("  SUPABASE_SERVICE_KEY=...")
    print("  SLACK_BOT_TOKEN=xoxb-...")
    print("  SYNC_CHANNELS=C0A474TT6CU")
    raise
