import logging
import random
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("RetryEngine")


@dataclass
class RetryConfig:
    max_attempts: int = 3
    base_delay: float = 2.0
    max_delay: float = 60.0
    retryable_status_codes: frozenset[int] = field(
        default_factory=lambda: frozenset({429, 500, 502, 503, 504})
    )


class RetryEngine:
    """
    Executes a callable with exponential backoff and full jitter.
    Classifies errors as: 429 rate-limited, retryable HTTP, permanent HTTP,
    transient network, or non-retryable (escalate immediately).
    Uses duck-typing on the exception's .response attribute to avoid
    coupling to a specific HTTP library's exception hierarchy.
    """

    def execute(
        self,
        fn: Callable[[], Any],
        config: RetryConfig,
        layer_name: str,
    ) -> Any:
        for attempt in range(1, config.max_attempts + 1):
            try:
                return fn()
            except Exception as e:
                response = getattr(e, "response", None)
                status = getattr(response, "status_code", 0) if response else 0

                if status == 429:
                    if attempt == config.max_attempts:
                        return None
                    wait = self._parse_retry_after(response) or self._jitter(
                        config.base_delay * (2**attempt), config.max_delay
                    )
                    logger.warning(
                        f"[{layer_name}] 429 rate-limited. "
                        f"Waiting {wait:.0f}s (attempt {attempt}/{config.max_attempts})"
                    )
                    time.sleep(wait)

                elif status in config.retryable_status_codes:
                    if attempt == config.max_attempts:
                        return None
                    delay = self._jitter(config.base_delay * (2**attempt), config.max_delay)
                    logger.warning(
                        f"[{layer_name}] HTTP {status} on attempt "
                        f"{attempt}/{config.max_attempts}. Backoff: {delay:.1f}s"
                    )
                    time.sleep(delay)

                elif status and status not in config.retryable_status_codes:
                    logger.warning(
                        f"[{layer_name}] Permanent HTTP {status}. Escalating to next layer."
                    )
                    return None

                elif isinstance(e, (ConnectionError, TimeoutError)):
                    if attempt == config.max_attempts:
                        return None
                    delay = self._jitter(config.base_delay * (2**attempt), config.max_delay)
                    logger.warning(
                        f"[{layer_name}] Transient {type(e).__name__} on attempt "
                        f"{attempt}/{config.max_attempts}. Backoff: {delay:.1f}s"
                    )
                    time.sleep(delay)

                else:
                    logger.warning(
                        f"[{layer_name}] Non-retryable error: "
                        f"{type(e).__name__}: {e}. Escalating to next layer."
                    )
                    return None

        return None

    @staticmethod
    def _jitter(delay: float, cap: float) -> float:
        """Full jitter: random value in [0, min(cap, delay)]."""
        return random.uniform(0, min(cap, delay))

    @staticmethod
    def _parse_retry_after(response: Any) -> float | None:
        if response is None:
            return None
        header = getattr(response.headers, "get", lambda k: None)("Retry-After")
        if header:
            try:
                return float(header)
            except ValueError:
                pass
        return None
