from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

logger = logging.getLogger("SchemaMonitor")


@dataclass
class ParseAttempt:
    timestamp: datetime
    url: str
    strategy_used: str | None   # None = all strategies failed
    success: bool


class SchemaHealthMonitor:
    """
    Tracks parse success rates in a rolling 30-minute window.
    Logs CRITICAL when success rate falls below 50% over >= 5 attempts.
    """

    WINDOW_MINUTES: int = 30
    DRIFT_THRESHOLD: float = 0.5
    MIN_SAMPLE_SIZE: int = 5

    def __init__(self) -> None:
        self._attempts: deque[ParseAttempt] = deque()

    def record(self, url: str, strategy: str | None, success: bool) -> None:
        self._attempts.append(
            ParseAttempt(datetime.now(timezone.utc), url, strategy, success)
        )
        self._evict_old()
        self._check_drift()

    def _evict_old(self) -> None:
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=self.WINDOW_MINUTES)
        while self._attempts and self._attempts[0].timestamp < cutoff:
            self._attempts.popleft()

    def _check_drift(self) -> None:
        recent = list(self._attempts)
        if len(recent) < self.MIN_SAMPLE_SIZE:
            return
        rate = sum(1 for a in recent if a.success) / len(recent)
        if rate < self.DRIFT_THRESHOLD:
            logger.critical(
                f"SCHEMA_DRIFT_DETECTED: Parse success rate {rate:.0%} "
                f"over last {len(recent)} attempts in {self.WINDOW_MINUTES}min window. "
                "Source site layout may have changed. Manual inspection required."
            )
