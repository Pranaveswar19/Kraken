"""Background sync scheduler using APScheduler."""

import logging
import json
from datetime import datetime
from pathlib import Path
from apscheduler.schedulers.background import BackgroundScheduler
from kraken.sync_tracker import SyncTracker
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.triggers.cron import CronTrigger
import time


logger = logging.getLogger(__name__)
_tracker = SyncTracker()


def sync_job(channel_id: str):
    """Scheduled sync job: fetch, enrich, embed, and store Slack messages."""
    from kraken.slack_sync import SlackSyncService
    from kraken.config import config

    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    logger.info(f"[{timestamp}] Sync started: channel={channel_id}")

    try:
        service = SlackSyncService(config.SLACK_BOT_TOKEN)

        sync_state_file = Path('.cache/slack_sync_state.json')
        sync_state = {}
        if sync_state_file.exists():
            try:
                with open(sync_state_file, 'r') as f:
                    sync_state = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load sync state: {e}, starting fresh")
                sync_state = {}

        last_ts = sync_state.get(channel_id, {}).get('last_message_ts')

        if last_ts:
            logger.info(f"  Incremental sync from timestamp: {last_ts}")
        else:
            logger.info(f"  Full sync (first time)")

        all_messages = []
        cursor = None
        page_count = 0

        while True:
            messages, cursor = service.fetch_messages(
                channel_id,
                oldest=last_ts,
                cursor=cursor,
                limit=100
            )
            all_messages.extend(messages)
            page_count += 1

            logger.info(f"  Page {page_count}: fetched {len(messages)} messages")

            if not cursor:
                break

            if page_count >= 10:
                logger.warning(f"  Reached page limit (10 pages), stopping")
                break

        logger.info(f"  Total fetched: {len(all_messages)} messages from Slack")

        if not all_messages:
            logger.info(f"  No new messages to sync")
            _tracker.record_success()
            return

        enriched = service.enrich_messages(all_messages, channel_id)
        logger.info(f"  Enriched {len(enriched)} user messages")

        if not enriched:
            logger.info(f"  No new user messages (all system messages)")
            _tracker.record_success()
            return

        embeddings = service.batch_embed(enriched)
        logger.info(f"  Generated {len(embeddings)} embeddings")

        count = service.upsert_to_db(enriched, embeddings)
        logger.info(f"[{timestamp}] Sync complete: {count} messages synced")

        if enriched:
            newest_ts = max(msg['timestamp'] for msg in enriched)
            sync_state[channel_id] = {
                'last_message_ts': newest_ts,
                'last_sync_at': datetime.now().isoformat()
            }

            try:
                sync_state_file.parent.mkdir(parents=True, exist_ok=True)
                with open(sync_state_file, 'w') as f:
                    json.dump(sync_state, f, indent=2)
                logger.info(f"  Updated sync state: last_ts={newest_ts}")
            except Exception as e:
                logger.warning(f"  Failed to save sync state: {e}")

        _tracker.record_success()

        alert = _tracker.should_alert()
        if alert:
            logger.warning(alert)

    except Exception as e:
        logger.error(f"[{timestamp}] Sync failed: {e}", exc_info=True)

        _tracker.record_failure(str(e))

        alert = _tracker.should_alert()
        if alert:
            logger.error(alert)


class SyncScheduler:
    """Runs sync jobs on a schedule. Jobs persist across restarts."""

    def __init__(self, db_path: str = 'jobs.sqlite'):
        """Create scheduler that saves jobs to SQLite."""
        jobstores = {
            'default': SQLAlchemyJobStore(url=f'sqlite:///{db_path}')
        }

        executors = {
            'default': ThreadPoolExecutor(max_workers=10)
        }

        job_defaults = {
            'coalesce': True,
            'max_instances': 1,
            'misfire_grace_time': 300
        }

        self.scheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults
        )

        self._running = False

        logger.info(f"Scheduler initialized with database: {db_path}")
    
    def add_hourly_sync(self, channel_id: str, interval_minutes: int = 60):
        """Schedule periodic sync for a channel."""
        job_id = f'sync_{channel_id}'

        if interval_minutes < 1 or interval_minutes > 1440:
            raise ValueError(f"Interval must be 1-1440 minutes, got {interval_minutes}")

        if interval_minutes < 60:
            trigger = CronTrigger(minute=f'*/{interval_minutes}')
            unit = f"{interval_minutes}m"
        else:
            interval_hours = interval_minutes // 60
            trigger = CronTrigger(hour=f'*/{interval_hours}', minute=0)
            unit = f"{interval_hours}h"

        self.scheduler.add_job(
            func=sync_job,
            trigger=trigger,
            args=[channel_id],
            id=job_id,
            replace_existing=True,
            name=f'Sync {channel_id} every {unit}'
        )

        logger.info(f"Scheduled sync for {channel_id} every {unit}")
    
    def start(self):
        """Start scheduler. Blocks until stop() called."""
        logger.info("Starting scheduler...")

        jobs = self.scheduler.get_jobs()
        logger.info(f"Found {len(jobs)} scheduled job(s)")

        for job in jobs:
            logger.info(f"  - {job.name}")

        logger.info("Scheduler is running. Press Ctrl+C to stop.")

        self.scheduler.start()
        self._running = True

        try:
            while self._running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()
    
    def stop(self):
        """Graceful shutdown."""
        logger.info("Stopping scheduler...")
        self._running = False
        self.scheduler.shutdown(wait=True)
        logger.info("Scheduler stopped")
