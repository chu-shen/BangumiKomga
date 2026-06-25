import atexit
from concurrent.futures import ThreadPoolExecutor
import logging

from config.config import (
    KOMGA_BASE_URL, KOMGA_EMAIL, KOMGA_EMAIL_PASSWORD,
    KOMGA_LIBRARY_LIST, KOMGA_COLLECTION_LIST,
)
from core.refresh_metadata import refresh_metadata, get_series_metadata
from api.komga_sse_api import KomgaSseClient

logger = logging.getLogger(__name__)

class SSEService:
    """基于 SSE 的元数据刷新服务.

    Series*/Book*: 匹配 libraryId → 刷新.
    Collection*:  匹配 collectionId → 刷新 seriesIds[] 中所有系列.
    两者独立过滤, 配置什么就处理什么.
    """

    def __init__(self, base_url=KOMGA_BASE_URL, username=KOMGA_EMAIL,
                 password=KOMGA_EMAIL_PASSWORD,
                 api_key=None, timeout=30, retries=5):
        self.client = KomgaSseClient(
            base_url, username, password, api_key, timeout, retries)
        self.client.on_event = self._on_event
        self.client.on_error = self._on_error

        self._executor = ThreadPoolExecutor(max_workers=5)

        # 静态过滤集 (仅 _on_event 所在线程访问, 无需锁)
        self._library_ids = {
            item["LIBRARY"] for item in KOMGA_LIBRARY_LIST
        } if KOMGA_LIBRARY_LIST else None

        self._collection_ids = {
            item["COLLECTION"] for item in KOMGA_COLLECTION_LIST
        } if KOMGA_COLLECTION_LIST else None

        atexit.register(self.stop)

    def start(self):
        self.client.start()

    def stop(self):
        self.client.stop()
        self._executor.shutdown(wait=True)
        logger.info("SSE 服务和线程池已关闭")

    # ---- SSE 事件回调 ----
    # _dispatch_event (Client层): JSON解析 + SubscribedEvents过滤 → 转发.
    # 能到达此处的事件都已通过 SubscribedEvents 过滤.
    # 这里按大类路由, per-event stub 保留作为文档和未来扩展点.

    def _on_event(self, event_type, event_data):
        logger.debug(f"捕获 SSE 事件 [{event_type}]: {event_data}")

        # ── 收藏集大类 ──
        if event_type.startswith("Collection"):
            if event_type == "CollectionAdded":
                self._handle_collection_event(event_type, event_data)
            elif event_type == "CollectionChanged":
                self._handle_collection_event(event_type, event_data)
            elif event_type == "CollectionDeleted":
                pass  # stub: 暂无处理

        # ── 系列大类 ──
        elif event_type.startswith("Series"):
            if event_type == "SeriesAdded":
                self._handle_series_event(event_type, event_data)
            elif event_type == "SeriesChanged":
                self._handle_series_event(event_type, event_data)
            elif event_type == "SeriesDeleted":
                pass  # stub: 暂无处理

        # ── 书籍大类 ──
        elif event_type.startswith("Book"):
            if event_type == "BookAdded":
                self._handle_series_event(event_type, event_data)
            elif event_type == "BookChanged":
                pass  # stub: 暂无处理
            elif event_type == "BookDeleted":
                pass  # stub: 暂无处理
            elif event_type == "BookImported":
                pass  # stub: adminOnly, 暂无处理

        # ── 库大类 ──
        elif event_type.startswith("Library"):
            pass  # stub: 暂无处理

        # ── 阅读列表大类 ──
        elif event_type.startswith("ReadList"):
            pass  # stub: 暂无处理

        # ── 阅读进度大类 ──
        elif event_type.startswith("ReadProgress"):
            pass  # stub: 暂无处理

        # ── 缩略图大类 ──
        elif event_type.startswith("Thumbnail"):
            pass  # stub: 暂无处理

        # ── 系统大类 ──
        elif event_type == "TaskQueueStatus" or event_type == "SessionExpired":
            pass  # stub: 系统事件, 忽略

        else:
            logger.debug(f"未知事件类型 [{event_type}]")

    def _handle_collection_event(self, event_type, event_data):
        collection_id = event_data.get("collectionId")
        series_ids = event_data.get("seriesIds", [])

        if self._collection_ids is None:
            return
        if collection_id not in self._collection_ids:
            logger.debug(
                f"收藏集 {collection_id} 不在 KOMGA_COLLECTION_LIST 中，跳过")
            return

        for sid in series_ids:
            self._executor.submit(
                _refresh_single_series, sid, event_type)

    def _handle_series_event(self, event_type, event_data):
        library_id = event_data.get("libraryId")
        series_id = event_data.get("seriesId")

        if self._library_ids is None:
            return
        if library_id not in self._library_ids:
            logger.debug(
                f"libraryId: {library_id} 不在 KOMGA_LIBRARY_LIST 中，跳过")
            return

        self._executor.submit(
            _refresh_single_series, series_id, event_type)

    def _on_error(self, e):
        logger.error(f"遇到 SSE 错误: {e}", exc_info=True)


# ---- 刷新逻辑 (线程池中执行) ----

def _refresh_single_series(series_id, event_type):
    """对单个系列执行元数据刷新."""
    try:
        series_detail = get_series_metadata([series_id])

        if event_type == "SeriesChanged":
            if not any(
                link["label"].lower() == "cbl"
                for link in series_detail[0]["metadata"]["links"]
            ):
                return

        refresh_metadata(series_detail)
    except Exception as e:
        logger.error(f"刷新系列 {series_id} 失败: {e}", exc_info=True)

def sse_service():
    """SSE 服务入口."""
    service = SSEService()
    service.start()

    try:
        # 等待 Ctrl+C 或 SSE 连接永久停止
        while not service.client.is_stopped():
            service.client.wait_stopped(timeout=5)
    except KeyboardInterrupt:
        pass
    finally:
        if service.client.is_stopped():
            logger.critical("SSE 连接已完全断开, 退出服务")
        service.stop()
        logger.warning("BangumiKomga SSE 服务已停止")
