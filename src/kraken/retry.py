"""Retry utilities for handling transient API failures."""

import time
import logging
from typing import Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar('T')

TRANSIENT_KEYWORDS = (
    'ratelimited',
    'rate_limit',
    'service_unavailable',
    'connection',
    'timeout',
    'temporary',
    '503',
    '502',
    '504',
    'writeerror',
    'readtimeout',
)


def is_transient_error(error: Exception) -> bool:
    """Determine if error is transient (should retry)."""
    error_str = str(error).lower()
    error_type = type(error).__name__.lower()

    return any(
        keyword in error_str or keyword in error_type
        for keyword in TRANSIENT_KEYWORDS
    )


def with_retry(
    func: Callable[[], T],
    max_retries: int = 3,
    backoff_base: float = 2.0,
    operation_name: str = "operation"
) -> T:
    """Execute function with exponential backoff retry on transient errors."""
    last_error = None

    for attempt in range(max_retries):
        try:
            return func()

        except Exception as e:
            last_error = e

            if not is_transient_error(e):
                logger.warning(
                    f"{operation_name} failed with permanent error: {e}"
                )
                raise

            if attempt >= max_retries - 1:
                logger.error(
                    f"{operation_name} failed after {max_retries} attempts: {e}"
                )
                raise

            delay = backoff_base ** attempt

            logger.warning(
                f"{operation_name} failed (attempt {attempt + 1}/{max_retries}), "
                f"retrying in {delay:.1f}s: {e}"
            )

            time.sleep(delay)

    raise last_error
