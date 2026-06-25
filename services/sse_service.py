import atexit
import threading
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

    过滤规则 (union):
      事件中的 series 属于配置的库 → 刷新
      事件中的 series 属于配置的收藏集 → 刷新
      两者都配置时, 满足任一即刷新

    收藏集白名单通过 CollectionAdded/Changed 事件实时维护,
    用于 Series/Book 事件的 collection 过滤 (SSE 事件不携带 collectionId).
    """

    def __init__(self, base_url=KOMGA_BASE_URL, username=KOMGA_EMAIL,
                 password=KOMGA_EMAIL_PASSWORD,
                 api_key=None, timeout=30, retries=5):
        self.client = KomgaSseClient(
            base_url, username, password, api_key, timeout, retries)
        self.client.on_event = self._on_event
        self.client.on_error = self._on_error

        self._executor = ThreadPoolExecutor(max_workers=5)

        # Library filter
        self._library_ids = {
            item["LIBRARY"] for item in KOMGA_LIBRARY_LIST
        } if KOMGA_LIBRARY_LIST else None

        # Collection filter — 关注的 collectionId + 白名单
        self._collection_ids = {
            item["COLLECTION"] for item in KOMGA_COLLECTION_LIST
        } if KOMGA_COLLECTION_LIST else None
        self._collection_series = set()

        # 启动时初始化白名单 (避免 Collection 事件到达前的空窗期)
        if self._collection_ids:
            self._init_collection_series()

        atexit.register(self.stop)

    def _init_collection_series(self):
        """加载所有配置的收藏集系列到白名单."""
        if self._collection_ids is None:
            return
        try:
            # 缓存 KomgaApi 实例, 避免重复导入
            if not hasattr(self, '_komga_api'):
                from api.komga_api import KomgaApi
                self._komga_api = KomgaApi(
                    KOMGA_BASE_URL, KOMGA_EMAIL, KOMGA_EMAIL_PASSWORD)
            self._collection_series.clear()
            for item in KOMGA_COLLECTION_LIST:
                result = self._komga_api.get_series_with_collection(
                    [item["COLLECTION"]])
                for s in result.get("content", []):
                    self._collection_series.add(s["id"])
            logger.info(
                f"已加载 {len(self._collection_series)} 个系列到收藏集白名单")
        except Exception as e:
            logger.warning(f"加载收藏集白名单失败: {e}，等待 SSE Collection 事件")

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

        if event_type == "CollectionAdded":
            self._collection_series.update(series_ids)
            # 新收藏集 → 刷新所有系列
            for sid in series_ids:
                self._executor.submit(
                    _refresh_single_series, sid, event_type)
        else:
            # CollectionChanged → 全量重查, 确保白名单中不再有被移除的系列
            self._init_collection_series()

    def _handle_series_event(self, event_type, event_data):
        library_id = event_data.get("libraryId")
        series_id = event_data.get("seriesId")

        # 未配置任何过滤 → 全部刷新
        if self._library_ids is None and self._collection_ids is None:
            self._executor.submit(
                _refresh_single_series, series_id, event_type)
            return

        # library 命中 → 刷新
        if self._library_ids and library_id in self._library_ids:
            self._executor.submit(
                _refresh_single_series, series_id, event_type)
            return

        # collection 白名单命中 → 刷新 (union)
        if series_id in self._collection_series:
            self._executor.submit(
                _refresh_single_series, series_id, event_type)
            return

        logger.debug(
            f"seriesId: {series_id} 不在配置的库/收藏集中，跳过")

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
