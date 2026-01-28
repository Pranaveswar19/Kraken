"""Start background Slack sync scheduler."""

import os
import sys
import signal
import argparse
import logging
from pathlib import Path
from typing import List

from kraken.scheduler import SyncScheduler
from kraken.config import config


def setup_logging(log_file: Path = None) -> None:
    """Configure dual logging (file + console)."""
    log_file = log_file or Path('logs') / 'sync.log'
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description='Run Kraken background sync')
    parser.add_argument(
        '--channels',
        help='Comma-separated channel IDs (overrides SYNC_CHANNELS env var)'
    )
    parser.add_argument(
        '--interval',
        type=int,
        help='Sync interval in MINUTES (overrides SYNC_INTERVAL_HOURS, accepts 1-1440)'
    )
    parser.add_argument('--log-file', type=Path, help='Log file path')
    return parser.parse_args()


def get_channels(args: argparse.Namespace) -> List[str]:
    """
    Get channel list with priority: CLI args > env var > error.
    
    Priority hierarchy:
    1. --channels CLI argument (explicit override)
    2. SYNC_CHANNELS env variable (standard config)
    3. Fail with clear error message
    
    Returns:
        List of validated channel IDs
        
    Raises:
        SystemExit: If no channels configured
    """
    logger = logging.getLogger(__name__)
    
    # Priority 1: CLI argument
    if args.channels:
        channels = [ch.strip() for ch in args.channels.split(',') if ch.strip()]
        logger.info(f"Using channels from CLI argument: {channels}")
        return channels
    
    # Priority 2: Environment variable
    try:
        config.validate_sync_config()
        channels = config.sync_channels_list
        logger.info(f"Using channels from SYNC_CHANNELS env var: {channels}")
        return channels
    except ValueError as e:
        logger.error(f"Channel configuration error: {e}")
        logger.error("")
        logger.error("Solutions:")
        logger.error("  1. Add to .env file: SYNC_CHANNELS=C0A474TT6CU")
        logger.error("  2. Use CLI flag: --channels C0A474TT6CU")
        sys.exit(1)


def get_interval(args: argparse.Namespace) -> int:
    """
    Get sync interval in minutes with priority: CLI > env var > default.
    
    Returns:
        Interval in minutes (1-1440)
    """
    logger = logging.getLogger(__name__)
    
    # Priority 1: CLI argument
    if args.interval is not None:
        if args.interval < 1 or args.interval > 1440:
            logger.error(f"Invalid --interval {args.interval}: must be 1-1440 minutes")
            sys.exit(1)
        
        unit = "minutes" if args.interval < 60 else "hours"
        display = args.interval if args.interval < 60 else args.interval // 60
        logger.info(f"Using interval from CLI: {display} {unit}")
        return args.interval
    
    # Priority 2: Environment variable
    interval = config.sync_interval_minutes
    
    unit = "minutes" if interval < 60 else "hours"
    display = interval if interval < 60 else interval // 60
    logger.info(f"Using interval from SYNC_INTERVAL_HOURS: {display} {unit}")
    
    return interval


# Global scheduler reference for signal handler
_scheduler = None


def signal_handler(signum, frame):
    """Handle Ctrl+C and termination signals."""
    global _scheduler
    logger = logging.getLogger(__name__)
    logger.info("\nShutdown signal received")
    if _scheduler:
        _scheduler.stop()
    sys.exit(0)


def main() -> None:
    """Main entry point."""
    global _scheduler
    
    args = parse_args()
    setup_logging(log_file=args.log_file)
    logger = logging.getLogger(__name__)
    
    # Get channels and interval (both fail fast if misconfigured)
    channels = get_channels(args)
    interval_minutes = get_interval(args)
    
    # Validate config
    try:
        config.validate()
        config.validate_sync_config()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    
    # Banner
    logger.info("="*60)
    logger.info("Kraken Background Sync Scheduler")
    logger.info("="*60)
    
    unit = "minutes" if interval_minutes < 60 else "hours"
    display = interval_minutes if interval_minutes < 60 else interval_minutes // 60
    logger.info(f"Sync interval: {display} {unit}")
    logger.info(f"Channels: {', '.join(channels)}")
    logger.info("")
    
    # Create scheduler
    try:
        _scheduler = SyncScheduler()
    except Exception as e:
        logger.error(f"Failed to initialize: {e}")
        sys.exit(2)
    
    # Add jobs for each channel
    for channel_id in channels:
        try:
            _scheduler.add_hourly_sync(channel_id, interval_minutes=interval_minutes)
            logger.info(f"✓ Scheduled sync for channel {channel_id}")
        except Exception as e:
            logger.error(f"✗ Failed to schedule {channel_id}: {e}")
            # Continue with other channels (degraded mode)
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("")
    logger.info("Press Ctrl+C to stop")
    logger.info("="*60)
    logger.info("")
    
    # Start (blocks until Ctrl+C)
    _scheduler.start()


if __name__ == '__main__':
    main()
