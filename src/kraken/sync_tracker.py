"""Track sync success/failure for monitoring and alerting."""

import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)


class SyncTracker:
    """Track sync outcomes for reliability monitoring. Alerts on repeated failures."""

    def __init__(self, state_file: Path = None):
        """Initialize tracker."""
        self.state_file = state_file or Path('.cache') / 'sync_state.json'
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self._state = self._load()
    
    def _load(self) -> dict:
        """Load state from disk."""
        if self.state_file.exists():
            try:
                with open(self.state_file) as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load sync state: {e}")

        return {
            'last_success': None,
            'last_failure': None,
            'consecutive_failures': 0,
            'failures_24h': []
        }

    def _save(self):
        """Save state to disk."""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self._state, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save sync state: {e}")
    
    def record_success(self):
        """Record successful sync. Resets consecutive failure counter."""
        self._state['last_success'] = datetime.now().isoformat()
        self._state['consecutive_failures'] = 0
        self._save()

        logger.debug("Sync success recorded")

    def record_failure(self, error: str):
        """Record failed sync."""
        now = datetime.now()
        self._state['last_failure'] = now.isoformat()
        self._state['consecutive_failures'] += 1

        cutoff = (now - timedelta(days=1)).timestamp()
        self._state['failures_24h'] = [
            ts for ts in self._state.get('failures_24h', [])
            if ts > cutoff
        ]
        self._state['failures_24h'].append(now.timestamp())

        self._save()

        logger.debug(f"Sync failure recorded: {error[:100]}")
    
    def should_alert(self) -> Optional[str]:
        """Check if we should alert on failures."""
        consecutive = self._state['consecutive_failures']
        failures_24h = len(self._state.get('failures_24h', []))

        if consecutive >= 3:
            return f"🚨 ALERT: {consecutive} consecutive sync failures - check config/auth"

        if failures_24h >= 10:
            return f"⚠️  ALERT: {failures_24h} failures in last 24 hours - API instability?"

        return None

    def get_stats(self) -> dict:
        """Get current sync statistics."""
        return {
            'last_success': self._state.get('last_success'),
            'last_failure': self._state.get('last_failure'),
            'consecutive_failures': self._state['consecutive_failures'],
            'failures_24h': len(self._state.get('failures_24h', []))
        }
