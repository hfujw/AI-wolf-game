import asyncio
import time
from functools import wraps
from typing import Callable, TypeVar, ParamSpec

P = ParamSpec('P')
T = TypeVar('T')

LLM_SEMAPHORE = asyncio.Semaphore(3)


class CircuitBreaker:
    """熔断器：连续失败 N 次后打开，冷却时间后进入半开状态"""

    def __init__(self, failure_threshold: int = 5, cooldown_seconds: float = 30.0):
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self.failure_count = 0
        self.last_failure_time: float = 0.0
        self.state = "closed"  # closed → open → half_open → closed

    def record_success(self):
        self.failure_count = 0
        self.state = "closed"

    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = "open"

    def allow_request(self) -> bool:
        if self.state == "closed":
            return True
        if self.state == "open":
            if time.time() - self.last_failure_time >= self.cooldown_seconds:
                self.state = "half_open"
                return True
            return False
        return True


_circuit_breaker = CircuitBreaker(failure_threshold=5, cooldown_seconds=30.0)


async def with_retry_and_circuit_breaker(
    func: Callable[P, T],
    *args: P.args,
    **kwargs: P.kwargs,
) -> T:
    """指数退避重试 + 熔断 + Semaphore 限流

    重试间隔: 1s → 2s → 4s（指数退避，最多3次尝试）
    """
    if not _circuit_breaker.allow_request():
        raise RuntimeError("Circuit breaker is OPEN. Too many LLM failures.")

    last_error = None
    for attempt in range(3):
        try:
            result = await asyncio.wait_for(func(*args, **kwargs), timeout=60)
            _circuit_breaker.record_success()
            return result
        except (asyncio.TimeoutError, Exception) as e:
            last_error = e
            _circuit_breaker.record_failure()
            if attempt < 2:
                wait = 2 ** attempt
                await asyncio.sleep(wait)

    raise RuntimeError(f"All 3 retry attempts failed. Last error: {last_error}")


async def semaphore_guard(func: Callable[P, T], *args: P.args, **kwargs: P.kwargs) -> T:
    """使用 Semaphore(3) 限制并发 LLM 调用"""
    async with LLM_SEMAPHORE:
        return await with_retry_and_circuit_breaker(func, *args, **kwargs)
