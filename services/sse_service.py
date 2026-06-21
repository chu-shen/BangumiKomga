import logging
import threading
import time

logger = logging.getLogger(__name__)
from config.config import KOMGA_LIBRARY_LIST
from core.refresh_metadata import refresh_metadata, get_series_metadata
from api.komga_sse_api import KomgaSseApi


class SseManager:
    """SSE 管理器 — 单层 daemon 线程监控连接健康，断线无限重连"""

    def __init__(self, stop_event):
        self._stop_event = stop_event
        self._thread = None
        self._sse_api = None

    def start(self):
        """启动 SSE 管理线程"""
        if self._thread and self._thread.is_alive():
            logger.warning("SseManager 已在运行")
            return
        self._thread = threading.Thread(
            target=self._run, daemon=True, name="SseManager"
        )
        self._thread.start()
        logger.info("SseManager 已启动")

    def stop(self):
        """停止 SSE 管理"""
        self._stop_event.set()
        if self._sse_api is not None:
            try:
                self._sse_api._stop_client()
            except Exception:
                logger.exception("停止 SSE 客户端时出错")
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=10)
        logger.info("SseManager 已停止")

    # ------------------------------------------------------------------
    # 主循环
    # ------------------------------------------------------------------
    def _run(self):
        """监控 SSE 连接线程，死亡时自动重建 (指数退避，无上限)"""
        consecutive_failures = 0

        while not self._stop_event.is_set():
            try:
                # 创建新的 SSE API 实例 (构造函数会自动启动 SSE 连接)
                self._sse_api = KomgaSseApi()
                self._sse_api.register_series_update_callback(_series_update_handler)
                logger.info("SSE 客户端已创建并启动")

                # 监控 SSE 客户端线程是否存活
                while not self._stop_event.is_set():
                    client_thread = getattr(self._sse_api.sse_client, 'thread', None)
                    if client_thread is None or not client_thread.is_alive():
                        logger.warning("检测到 SSE 客户端线程退出")
                        break
                    self._stop_event.wait(2)  # 每 2 秒检查一次

                # 如果是因为 stop_event 退出，不再重连
                if self._stop_event.is_set():
                    break

                consecutive_failures += 1

            except Exception:
                logger.exception("SseManager 异常")
                consecutive_failures += 1

            # 停止旧实例
            if self._sse_api is not None:
                try:
                    self._sse_api._stop_client()
                except Exception:
                    pass
                self._sse_api = None

            if self._stop_event.is_set():
                break

            # 指数退避 (1s → 2s → 4s → ... → 60s 封顶)
            backoff = min(2 ** consecutive_failures, 60)
            logger.info("SSE 将在 %d 秒后重连 (第 %d 次)", backoff, consecutive_failures)
            self._stop_event.wait(backoff)


# ---------------------------------------------------------------------------
# SSE 事件处理器 (模块级函数，避免持有 SseManager 引用)
# ---------------------------------------------------------------------------
def _is_surveilled_library(library_id):
    if KOMGA_LIBRARY_LIST:
        KOMGA_LIBRARIES = {item["LIBRARY"] for item in KOMGA_LIBRARY_LIST}
        return library_id not in KOMGA_LIBRARIES
    return False


def _series_update_handler(data):
    """处理 Komga SSE 系列更新事件"""
    series_id = data["event_data"]["seriesId"]
    library_id = data["event_data"]["libraryId"]

    try:
        series_detail = get_series_metadata([series_id])
    except Exception:
        logger.exception("获取系列元数据失败: %s", series_id)
        return

    # 筛选有效的 SeriesChanged 事件
    if data["event_type"] == "SeriesChanged":
        try:
            if not any(
                link["label"].lower() == "cbl"
                for link in series_detail[0]["metadata"]["links"]
            ):
                return  # 无 CBL 链接，忽略
        except (IndexError, KeyError):
            return

    if _is_surveilled_library(library_id):
        logger.info("library %s 不在监控范围内，跳过", library_id)
    else:
        try:
            refresh_metadata(series_detail)
        except Exception:
            logger.exception("刷新元数据失败")


# ---------------------------------------------------------------------------
# 向后兼容入口 (已废弃)
# ---------------------------------------------------------------------------
def sse_service():
    """@deprecated: 使用 SseManager 代替"""
    logger.warning("sse_service() 已废弃，请使用 SseManager")
    mgr = SseManager(threading.Event())
    mgr.start()
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        logger.warning("服务手动终止")
        mgr.stop()
