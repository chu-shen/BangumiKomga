"""基于轮询的元数据刷新服务.

在增量刷新与全量刷新之间交替:
  增量: 通过 Komga /series/latest 获取最近修改的系列.
  全量: 刷新 KOMGA_LIBRARY_LIST / KOMGA_COLLECTION_LIST 中的所有系列.

全量刷新间隔基于墙钟时间, 从现有配置计算:
  POLL_INTERVAL × POLL_REFRESH_ALL_METADATA_INTERVAL.
"""

import os
import threading
import logging
from datetime import datetime, timezone

from config.config import (
    BANGUMI_KOMGA_SERVICE_POLL_INTERVAL,
    BANGUMI_KOMGA_SERVICE_POLL_REFRESH_ALL_METADATA_INTERVAL,
    ARCHIVE_FILES_DIR,
)
from core.refresh_metadata import refresh_metadata, refresh_partial_metadata
from tools.cache_time import TimeCacheManager

logger = logging.getLogger(__name__)


class PollService:
    """定时轮询元数据刷新服务."""

    def __init__(self):
        self._interval = BANGUMI_KOMGA_SERVICE_POLL_INTERVAL
        # 向后兼容: 将轮询周期计数转换为秒
        self._full_refresh_seconds = (
            BANGUMI_KOMGA_SERVICE_POLL_INTERVAL
            * BANGUMI_KOMGA_SERVICE_POLL_REFRESH_ALL_METADATA_INTERVAL
        )
        self._full_refresh_cache = os.path.join(
            ARCHIVE_FILES_DIR, "poll_last_full_refresh.json"
        )

        self._running = False
        self._stop_event = threading.Event()
        self._thread = None

    # -- 公开 API ----------------------------------------------------

    def start(self):
        """在非守护线程中启动轮询."""
        if self._running:
            return
        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=False)
        self._thread.start()

    def stop(self):
        """停止轮询并等待当前周期结束."""
        self._running = False
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=30)

    # -- 内部实现 ----------------------------------------------------

    def _run(self):
        """轮询主循环."""
        while self._running:
            try:
                self._tick()
            except Exception:
                logger.error("轮询周期失败", exc_info=True)

            # 可中断的 sleep — stop() 会 set 事件
            if self._stop_event.wait(timeout=self._interval):
                break

    def _tick(self):
        """单次轮询周期: 判断全量/增量, 执行刷新."""
        if self._should_full_refresh():
            logger.info("开始全量元数据刷新")
            refresh_metadata()
            self._save_full_refresh_time()
        else:
            refresh_partial_metadata()

    def _should_full_refresh(self) -> bool:
        """距上次全量刷新是否已过足够时间."""
        last = TimeCacheManager.read_time(self._full_refresh_cache)
        last_dt = TimeCacheManager.convert_to_datetime(last)
        if last_dt is None:
            return True
        elapsed = (datetime.now(timezone.utc) - last_dt).total_seconds()
        return elapsed >= self._full_refresh_seconds

    def _save_full_refresh_time(self):
        os.makedirs(ARCHIVE_FILES_DIR, exist_ok=True)
        TimeCacheManager.save_time(
            self._full_refresh_cache,
            datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        )


def poll_service():
    """轮询模式入口 — 阻塞主线程, Ctrl+C / SIGTERM 退出."""
    service = PollService()
    service.start()
    try:
        # 用超时轮询替代永久阻塞, 确保 SIGTERM 能被及时处理
        while service._running:
            service._stop_event.wait(timeout=5)
    except KeyboardInterrupt:
        pass
    finally:
        service.stop()
        logger.info("轮询服务已停止")
