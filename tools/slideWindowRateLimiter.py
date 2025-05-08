import time
from collections import deque
from functools import wraps
from tools.log import logger


class SlideWindowCounter:
    """线程安全的滑动窗口限流器"""

    def __init__(self, max_requests: int, window_seconds: float):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = deque()

    def is_allowed(self) -> bool:
        """检查是否允许请求"""
        current_time = time.time()
        # 清理过期请求
        while self.requests and current_time - self.requests[0] > self.window_seconds:
            expired_time = self.requests.popleft()
            logger.debug(f"时间: {time.time():.2f} | 移除过期请求")
        if len(self.requests) < self.max_requests:
            self.requests.append(current_time)
            logger.debug(
                f"时间: {time.time():.2f} | 允许请求 | 剩余: {self.remaining_requests()})"
            )
            return True
        else:
            logger.debug(
                f"时间: {time.time():.2f} | 拒绝请求 | max reached: {self.max_requests})"
            )
            return False

    def remaining_requests(self) -> int:
        """获取剩余可用请求数"""
        return self.max_requests - len(self.requests)

# 参数设置参考：https://docs.anilist.co/guide/rate-limiting
def SlideWindowRateLimiter(
    max_requests: int = 90,
    window_seconds: float = 60,
    max_retries: int = 3,
    delay: float = 1,
):
    def decorator(func):
        limiter = SlideWindowCounter(max_requests, window_seconds)

        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while retries <= max_retries:
                if limiter.is_allowed():
                    return func(*args, **kwargs)
                else:
                    try:
                        if retries >= max_retries:  # 最后一次重试失败
                            raise Exception(f"达到最大重试次数({max_retries})")
                    except Exception as e:
                        print(e)
                    time.sleep(delay)
                    retries += 1

        return wrapper

    return decorator
