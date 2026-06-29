# -*- coding: utf-8 -*- #
# ------------------------------------------------------------------
# Discussion: https://github.com/gotson/komga/discussions/1963
# Description: Komga SSE Service
# ------------------------------------------------------------------


import threading
import time
import json
import requests
import base64
from urllib3.util import Retry
from requests.adapters import HTTPAdapter
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
import logging
logger = logging.getLogger(__name__)
from config.config import KOMGA_BASE_URL, KOMGA_EMAIL, KOMGA_EMAIL_PASSWORD, KOMGA_LIBRARY_LIST

# ==========================================================================
# Komga SSE 事件类型完整参考
# 来源: komga/src/main/kotlin/org/gotson/komga/interfaces/sse/SseController.kt
# 订阅及处理逻辑见: services/sse_service.py -> SSEService._on_event()
# ==========================================================================
#
# ── 系列 (seriesId, libraryId) ────────────────────────────────────────
# SeriesAdded    : { seriesId: str, libraryId: str }
#                  新系列添加到库时触发 → 需要刷新元数据
# SeriesChanged  : { seriesId: str, libraryId: str }
#                  系列元数据/文件变更时触发。注意: 扫描库会触发全库系列
#                  的此事件 → 需结合 CBL 判断是否实际需要刷新
# SeriesDeleted  : { seriesId: str, libraryId: str }
#                  系列删除时触发 → 通常无需处理
#
# ── 书籍 (bookId, seriesId, libraryId) ────────────────────────────────
# BookAdded      : { bookId: str, seriesId: str, libraryId: str }
#                  新书添加到系列时触发 (e.g. 追连载出新话) → 需刷新
# BookChanged    : { bookId: str, seriesId: str, libraryId: str }
#                  书籍元数据变更时触发 → 频繁, 一般无需处理
# BookDeleted    : { bookId: str, seriesId: str, libraryId: str }
#                  书籍删除时触发 → 无需处理
# BookImported   : { bookId: str?, sourceFile: str, success: bool, message: str? }
#                  书籍导入完成时触发 (adminOnly) → 一般无需处理
#
# ── 收藏集 (collectionId, seriesIds[]) ─────────────────────────────────
# CollectionAdded   : { collectionId: str, seriesIds: Array<str> }
#                     新收藏集创建时触发, 携带全量 seriesIds
# CollectionChanged : { collectionId: str, seriesIds: Array<str> }
#                     收藏集修改(添加/移除系列)时触发, 携带全量 seriesIds
# CollectionDeleted : { collectionId: str, seriesIds: Array<str> }
#                     收藏集删除时触发 → 携带被删时的 seriesIds
#                     ★ 用这三个事件可实时维护收藏集会员白名单, 无需额外 API 查询
#
# ── 库 (libraryId) ────────────────────────────────────────────────────
# LibraryAdded   : { libraryId: str }
# LibraryChanged : { libraryId: str }
# LibraryDeleted : { libraryId: str }
#
# ── 阅读列表 (readListId, bookIds[]) ──────────────────────────────────
# ReadListAdded   : { readListId: str, bookIds: Array<str> }
# ReadListChanged : { readListId: str, bookIds: Array<str> }
# ReadListDeleted : { readListId: str, bookIds: Array<str> }
#
# ── 阅读进度 (userId scoped) ─────────────────────────────────────────
# ReadProgressChanged       : { bookId: str, userId: str }
# ReadProgressDeleted       : { bookId: str, userId: str }
# ReadProgressSeriesChanged : { seriesId: str, userId: str }
# ReadProgressSeriesDeleted : { seriesId: str, userId: str }
#
# ── 缩略图 ────────────────────────────────────────────────────────────
# ThumbnailBookAdded              : { bookId: str, seriesId: str, selected: bool }
# ThumbnailBookDeleted            : { ... }
# ThumbnailSeriesAdded            : { seriesId: str, selected: bool }
# ThumbnailSeriesDeleted          : { ... }
# ThumbnailSeriesCollectionAdded  : { collectionId: str, selected: bool }
# ThumbnailSeriesCollectionDeleted: { ... }
# ThumbnailReadListAdded          : { readListId: str, selected: bool }
# ThumbnailReadListDeleted        : { ... }
#
# ── 系统 (adminOnly / userIdOnly) ────────────────────────────────────
# TaskQueueStatus : { count: int, countByType: Dict<str, int> }
#                   定时 10s 发送, adminOnly → 忽略
# SessionExpired  : { userId: str }
#                   用户会话过期时触发, userIdOnly → 忽略
# ==========================================================================


# -- 当前订阅的事件 -----------------------------------------------
# 只有在此声明的事件才会被 _dispatch_event 转发给 Service 层.
SubscribedEvents = [
    "SeriesAdded",
    "SeriesChanged",
    "BookAdded",
    "CollectionAdded",
    "CollectionChanged",
]


class KomgaSseClient:
    """纯 SSE 协议客户端: 连接 Komga, 解析事件流, 回调每条事件."""

    def __init__(self, base_url, username, password,
                 api_key=None, timeout=30, retries=5):
        self.base_url = base_url
        self.url = f"{base_url}/sse/v1/events"
        self.auth = (username, password)
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = retries

        # 连接状态
        self._running = False
        self._thread = None
        self._response = None       # 追踪当前响应对象, 用于 clean close
        self._delay = 1
        self._stopped = threading.Event()   # 重连耗尽时 set, 主线程可感知

        # 默认回调
        self.on_open = lambda: logger.info("成功连接 Komga SSE 服务端点")
        self.on_close = lambda: logger.info("正常关闭 Komga SSE 连接")
        self.on_error = lambda err: logger.error(
            f"Komga SSE 错误: {err}", exc_info=True)
        self.on_event = lambda event_type, data: logger.debug(
            f"SSE event [{event_type}]: {data}")

        self.session = self._create_session()
        self._setup_headers()

    # ------------------------------------------------------------------
    # 公开 API
    # ------------------------------------------------------------------

    def start(self):
        """启动 SSE 连接 (非阻塞). 认证失败时立即退出."""
        if self._running:
            return
        if self._stopped.is_set():
            logger.error("SSE 认证失败, 拒绝启动")
            return
        self._running = True
        self._thread = threading.Thread(target=self._connect, daemon=False)
        self._thread.start()

    def stop(self):
        """停止 SSE 连接并等待线程结束."""
        self._running = False
        if self._response is not None:
            try:
                self._response.close()
            except Exception:
                pass
        if self._thread is not None:
            self._thread.join(timeout=10)
        try:
            self.session.close()
        except Exception:
            pass
        self.on_close()

    def is_stopped(self) -> bool:
        """SSE 连接是否已永久停止 (重连耗尽或非200响应)."""
        return self._stopped.is_set()

    def wait_stopped(self, timeout=None) -> bool:
        """阻塞等待 SSE 连接停止, 返回是否已停止. 可 Ctrl+C 中断."""
        return self._stopped.wait(timeout=timeout)

    # ------------------------------------------------------------------
    # 内部实现
    # ------------------------------------------------------------------

    def _create_session(self, pool_size=5) -> requests.Session:
        session = requests.Session()
        retries = Retry(
            total=self.max_retries,
            backoff_factor=0.5,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["HEAD", "GET"],
        )
        adapter = HTTPAdapter(
            max_retries=retries,
            pool_connections=pool_size,
            pool_maxsize=pool_size,
        )
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def _setup_headers(self):
        """设置请求头并验证身份."""
        headers = {
            "Accept": "text/event-stream",
            "User-Agent": (
                "chu-shen/BangumiKomga "
                "(https://github.com/chu-shen/BangumiKomga)"
            ),
            "Cache-Control": "no-cache",
        }

        if self.api_key:
            headers["X-API-Key"] = self.api_key
            self.session.headers.update(headers)
            test_url = f"{self.base_url}/api/v2/users/me"
            try:
                with self.session.get(test_url) as resp:
                    if resp.status_code != 200:
                        logger.error(
                            f"Komga SSE API_KEY 验证失败: {resp.status_code}")
                        self._stopped.set()
                        return
            except requests.exceptions.RequestException as e:
                logger.error(f"API_KEY 身份验证失败: {e}")
                self._stopped.set()
                return
        elif self.auth:
            credentials = f"{self.auth[0]}:{self.auth[1]}"
            encoded = base64.b64encode(
                credentials.encode("utf-8")).decode("utf-8")
            headers["Authorization"] = f"Basic {encoded}"
            self.session.headers.update(headers)
            try:
                with self.session.get(
                    self.url, stream=True, timeout=self.timeout
                ) as resp:
                    if resp.status_code != 200:
                        logger.error("Komga 账户凭据验证失败")
                        self._stopped.set()
                        return
            except requests.exceptions.ConnectionError:
                logger.error("Komga SSE 连接错误: 无法连接至服务器")
                self._stopped.set()
                return
            except Exception as e:
                logger.error(f"Komga SSE 连接错误: {e}")
                self.on_error(e)
                self._stopped.set()
                return
        else:
            logger.error("Komga SSE 认证失败: 未配置 api_key 或 auth")
            self._stopped.set()
            return

    def _connect(self):
        """SSE 连接含重连的主循环."""
        retry_count = 0
        while self._running:
            try:
                with self.session.get(
                    self.url, stream=True, timeout=self.timeout
                ) as resp:
                    self._response = resp
                    if resp.status_code != 200:
                        self.on_error(
                            f"Komga SSE 连接失败, "
                            f"HTTP {resp.status_code}: {resp.reason}")
                        self._running = False
                        self._stopped.set()  # 非 200 响应, 停止重连
                        break

                    self.on_open()
                    self._process_stream(resp)
                    retry_count = 0  # 成功后重置计数

            except Exception as e:
                logger.error(f"Komga SSE 连接出错: {e}", exc_info=True)
                self.on_error(e)
                retry_count += 1
                if retry_count > self.max_retries:
                    logger.error("超过最大重试次数，停止连接")
                    self._running = False   # B4 fix: 不调用 stop() 避免 self-join
                    self._stopped.set()     # 通知主线程: SSE 连接已完全断开
                    return
                delay = min(self._delay * (2 ** retry_count), 30)
                logger.info(f"将在 {delay} 秒后尝试重连...")
                time.sleep(delay)
            finally:
                self._response = None

    def _process_stream(self, response):
        """解析 SSE 事件流."""
        current_event = ""
        current_data = ""
        try:
            for line in response.iter_lines(decode_unicode=True):
                if not self._running:
                    break
                try:
                    if line:
                        current_event, current_data = self._parse_message_line(
                            line, current_event, current_data)
                    else:
                        # 空行分隔事件
                        self._dispatch_event(
                            current_event, current_data)
                        current_event = ""
                        current_data = ""
                except Exception as e:
                    self.on_error(
                        f"SSE 数据行 {line} 处理异常: {e}")
                    continue
        except requests.exceptions.RequestException as re:
            logger.error(
                f"读取 SSE 流数据时网络连接中断: {re}")
            self.on_error(re)
        except Exception as e:
            self.on_error(f"遇到未知错误: {e}")

    def _parse_message_line(self, line, current_event, current_data):
        """解析单行 SSE 消息."""
        if not line:
            return current_event, current_data

        if line.startswith("event:"):
            current_event = line[6:].strip()
        elif line.startswith("data:"):
            data_part = line[5:].strip()
            if not current_data:
                current_data = data_part
            else:
                current_data += "\n" + data_part
        return current_event, current_data

    def _dispatch_event(self, event_type, data):
        """分发完整事件: JSON解析 → 过滤非订阅事件 → 转发到 on_event."""
        if data is None or (isinstance(data, str) and not data.strip()):
            return

        try:
            json_data = json.loads(data) if isinstance(data, str) else data
            if not isinstance(json_data, dict):
                raise ValueError("事件数据不是有效的 JSON 格式")

            if event_type in SubscribedEvents:
                self.on_event(event_type, json_data)
            else:
                logger.debug(f"忽略非订阅事件 [{event_type}]: {data}")
        except json.JSONDecodeError as e:
            self.on_error(f"事件数据的格式错误: {data}, {e}")
        except Exception as e:
            self.on_error(f"事件 {event_type} 分发出错: {e}")
