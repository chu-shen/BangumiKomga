import logging
import threading
import time

logger = logging.getLogger(__name__)
from config.config import (
    BANGUMI_KOMGA_SERVICE_POLL_INTERVAL,
    BANGUMI_KOMGA_SERVICE_POLL_REFRESH_ALL_METADATA_INTERVAL,
)
from core.refresh_metadata import refresh_metadata, refresh_partial_metadata


class PollManager:
    """轮询管理器 — 单层 daemon 线程，用 stop_event 控制生命周期"""

    def __init__(self, stop_event, poll_interval=None, full_refresh_interval=None):
        self._stop_event = stop_event
        self._poll_interval = poll_interval or BANGUMI_KOMGA_SERVICE_POLL_INTERVAL
        self._full_refresh_interval = (
            full_refresh_interval
            or BANGUMI_KOMGA_SERVICE_POLL_REFRESH_ALL_METADATA_INTERVAL
        )
        self._thread = None
        self._refresh_lock = threading.Lock()
        self._refresh_counter = 0

    def start(self):
        """启动轮询线程"""
        if self._thread and self._thread.is_alive():
            logger.warning("PollManager 已在运行")
            return
        self._thread = threading.Thread(
            target=self._run, daemon=True, name="PollManager"
        )
        self._thread.start()
        logger.info("PollManager 已启动 (间隔=%ds, 全量刷新间隔=%d次)",
                     self._poll_interval, self._full_refresh_interval)

    def stop(self):
        """停止轮询"""
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=30)
        logger.info("PollManager 已停止")

    def _run(self):
        """轮询主循环"""
        while not self._stop_event.is_set():
            try:
                if self._refresh_counter >= self._full_refresh_interval:
                    self._safe_refresh(refresh_metadata)
                    self._refresh_counter = 0
                else:
                    self._safe_refresh(refresh_partial_metadata)
                self._refresh_counter += 1
            except Exception:
                logger.exception("轮询循环异常")

            # 用可中断的 wait 代替 time.sleep
            self._stop_event.wait(self._poll_interval)

    def _safe_refresh(self, refresh_func):
        """加锁保护，防止并发刷新"""
        if not self._refresh_lock.acquire(blocking=False):
            logger.warning("上一轮刷新尚未完成，跳过本次")
            return
        try:
            refresh_func()
        except Exception:
            logger.exception("刷新失败")
        finally:
            self._refresh_lock.release()

def poll_service():
    """@deprecated: 使用 PollManager 代替"""
    logger.warning("poll_service() 已废弃，请使用 PollManager")
    mgr = PollManager(threading.Event())
    mgr.start()
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        logger.warning("服务手动终止")

