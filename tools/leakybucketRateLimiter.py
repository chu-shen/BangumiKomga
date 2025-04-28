import time
from typing import Tuple
import asyncio
import threading
from functools import wraps


class LeakyBucket:
    def __init__(self, capacity: int, fill_rate: float):
        self.capacity = capacity
        self.fill_rate = fill_rate
        self.tokens = 0.0
        self.last_refill_time = time.time()
        # self.lock = asyncio.Lock()  # 线程安全锁

    def _refill_tokens(self):
        # async with self.lock:
        now = time.time()
        delta = (now - self.last_refill_time) * self.fill_rate
        self.tokens = min(self.capacity, self.tokens + delta)
        self.last_refill_time = now
        print(
            f"时间: {now:.2f} | 补充令牌: {delta:.2f} | 当前令牌: {self.tokens:.2f}", flush=True)

    def allow_request(self) -> Tuple[bool, float]:
        # async with self.lock:
        self._refill_tokens()
        if self.tokens >= 1:
            self.tokens -= 1
            print(
                f"时间: {time.time():.2f} | 允许请求 | 消耗1令牌 | 剩余: {self.tokens:.2f}", flush=True)
            return (True, 0.0)
        else:
            wait_time = (1 - self.tokens) / self.fill_rate
            print(
                f"时间: {time.time():.2f} | 拒绝请求 | 当前令牌: {self.tokens:.2f} | 需等待: {wait_time:.3f}秒", flush=True)
            return (False, round(wait_time, 3))


def LeakyBucketRateLimiter(capacity: int, fill_rate: float, max_retries=3):
    def decorator(func):
        bucket = LeakyBucket(capacity, fill_rate)

        @wraps(func)
        def wrapper(*args, **kwargs):
            retry_count = 0
            while True:
                allowed, wait = bucket.allow_request()
                if allowed:
                    return func(*args, **kwargs)

                else:
                    try:
                        if max_retries == 0:
                            raise Exception("不允许重试")
                        if max_retries != 0 and retry_count < max_retries:
                            raise Exception("达到最大重试次数")
                    except Exception as e:
                        time.sleep(wait)
                        # time.sleep(wait * (2 ** retry_count))
                        retry_count += 1
        return wrapper
    return decorator
