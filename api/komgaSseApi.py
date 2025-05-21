# -*- coding: utf-8 -*- #
# ------------------------------------------------------------------
# Discussion: https://github.com/gotson/komga/discussions/1963
# Description: Komga SSE Service(https://github.com/gotson/komga/blob/0a2c3ace2883b5c9d8be4b5235a5b0db107eba5e/komga-webui/src/services/komga-sse.service.ts)
# ------------------------------------------------------------------


from config.config import KOMGA_BASE_URL, KOMGA_EMAIL, KOMGA_EMAIL_PASSWORD, KOMGA_LIBRARY_LIST
import time
import json
from tools.log import logger
import requests
from requests.adapters import HTTPAdapter
from threading import Thread, Lock
import base64

# 可配置的订阅事件类型
RefreshEventType = ["SeriesAdded",
                    # 扫描库文件(深度)会触发全库系列的 `SeriesChanged` 事件, 需要结合CBL判断是否实际需要刷新
                    # 在系列添加时只需关注 `SeriesAdded` 事件即可
                    "SeriesChanged",
                    # [TaskQueueStatus]: {"count":0,"countByType":{}} 会自动定时触发, 应该忽略
                    #  "TaskQueueStatus",
                    # `BookAdded`是在系列中更新新章节时(e.g.追连载)应关注的事件
                    "BookAdded",
                    # `BookChanged`是在系列中更新新一个章节时会多次触发的事件, 感觉应该无视它
                    # "BookChanged",

                    # `BookImported` 我还没见过, 可能是我从来不用导入功能
                    # "BookImported"
                    ]


class KomgaSseClient:
    def __init__(self, base_url, username, password, api_key=None, timeout=30, retries=5):
        self.url = f"{base_url}/sse/v1/events"
        self.auth = (username, password)
        self.running = False
        self.timeout = timeout
        self.thread = None
        self.delay = 1
        self.max_retries = retries

        # 用于Debug的默认回调函数
        self.on_open = lambda: logger.info("成功连接 Komga SSE 服务端点")
        self.on_close = lambda: logger.info("正常关闭 Komga SSE 连接")
        self.on_error = lambda err: logger.info(f"出现错误: {err}")
        self.on_message = lambda msg: logger.info(f"SSE消息内容: {msg}")
        self.on_retry = lambda: logger.info("正在重连...")
        self.on_event = lambda event_type, data: logger.info(
            f"Event [{event_type}]: {data}")

        self.session = requests.Session()
        # 传输层自动重连, 重试 self.max_retries 次
        self.session.mount(
            "http://", HTTPAdapter(max_retries=self.max_retries))
        self.session.mount(
            "https://", HTTPAdapter(max_retries=self.max_retries))
        self.session.headers.update(
            {
                # 客户端向服务器表明自身能够接收事件流格式数据的关键标识
                # 见MDN: https://developer.mozilla.org/zh-CN/docs/Web/API/Server-sent_events/Using_server-sent_events
                "Accept": "text/event-stream",
                "User-Agent": "chu-shen/BangumiKomga (https://github.com/chu-shen/BangumiKomga)",
                # 防止缓存干扰实时数据流
                "Cache-Control": "no-cache",
            }
        )
        # 使用API_KEY
        if api_key:
            self.session.headers["X-API-Key"] = api_key
            test_url = f"{base_url}/api/v2/users/me"
            response = self.session.get(test_url)
        # 使用账号凭据
        else:
            # 构建认证字符串
            credentials = f"{self.auth[0]}:{self.auth[1]}"
            encoded = base64.b64encode(
                credentials.encode("utf-8")).decode("utf-8")
            auth_text = f"Basic {encoded}"
            # 向header加入认证字段
            self.session.headers.update(
                {
                    "Authorization": auth_text
                }
            )
            # 测试连接
            try:
                response = self.session.get(
                    self.url,
                    stream=True,
                    timeout=self.timeout
                )
            except Exception as e:
                logger.error(
                    f"Komga SSE 连接失败, HTTP {response.status_code}: {response.reason}")
                self.on_error(e)
                exit(1)
        if response.status_code != 200:
            logger.error("Komga 身份验证失败!")
            return

    def start(self):
        """启动 SSE 监听"""
        if self.running:
            return

        self.running = True
        self.thread = Thread(target=self._connect)
        self.thread.start()

    def stop(self):
        """停止 SSE 监听"""
        self.running = False
        if self.thread:
            self.thread.join()
        # 释放 Session
        self.session.close()
        self.on_close()

    def _connect(self):
        """建立 SSE 连接"""
        retry_count = 0
        while self.running:
            try:
                with self.session.get(self.url,
                                      stream=True,
                                      timeout=self.timeout) as response:
                    if response.status_code != 200:
                        self.on_error(
                            f"Komga SSE 连接失败, HTTP {response.status_code}: {response.reason}")
                        return

                    self.on_open()
                    self._process_stream(response)
                    retry_count = 0  # 成功后重置重试计数

            except Exception as e:
                logger.error(f"Komga SSE 连接出错: {e}")
                self.on_error(e)
                retry_count += 1
                # 应用层自动重连, 重试self.max_retries次
                if retry_count > self.max_retries:
                    logger.error("超过最大重试次数，停止连接")
                    self.stop()
                    return
                # 指数退避
                delay = min(self.delay * (2 ** retry_count), 30)
                logger.info(f"将在 {delay} 秒后尝试重连...")
                time.sleep(delay)
                self.on_retry()

    def _process_stream(self, response):
        """解析事件流"""
        buffer = ""
        for chunk in response.iter_content(chunk_size=1024, decode_unicode=True):
            if not self.running:
                break

            buffer += chunk
            lines = buffer.split("\n")

            # 保留未完整行
            if buffer.endswith("\n"):
                buffer = ""
            else:
                buffer = lines[-1]
                lines = lines[:-1]

            for line in lines:
                if not line.strip():
                    continue

                # 解析事件类型
                if line.startswith("event:"):
                    current_event = line[6:].strip()
                    continue

                # 解析数据
                if line.startswith("data:"):
                    data = line[5:].strip()
                    if data:
                        self._dispatch_event(current_event, data)
                        # 重置为空
                        current_event = ""

    def _dispatch_event(self, event_type, data):
        """分发事件到对应处理器"""
        # 忽略refresh_event_type外的其他事件类型
        if event_type in RefreshEventType:
            self.on_event(event_type, data)
        else:
            self.on_message(data)


class KomgaSseApi:
    def __init__(self, base_url=KOMGA_BASE_URL, username=KOMGA_EMAIL, password=KOMGA_EMAIL_PASSWORD, api_key=None, timeout=30, retries=5):
        # 实例化 KomgaSseApi 对象
        self.sse_client = KomgaSseClient(
            base_url, username, password, api_key, timeout, retries)

        self.series_modified_callbacks = []
        self.series_callback_lock = Lock()

        # 绑定回调
        self.sse_client.on_message = self.on_message
        self.sse_client.on_error = self.on_error
        self.sse_client.on_event = self.on_event

        # 使用守护线程启动SSE客户端
        self.sse_thread = Thread(target=self._start_client, daemon=True)
        self.series_modified_callbacks = []
        self.series_callback_lock = Lock()
        self.sse_thread.start()  # 立即启动线程

    def _start_client(self):
        try:
            self.sse_client.start()
            while True:
                time.sleep(5)  # 保持主线程运行
        except KeyboardInterrupt:
            logger.warning("正在关闭SSE连接...")
            self.sse_client.stop()

    def register_series_update_callback(self, callback):
        """注册系列更新回调函数"""
        # with self.series_callback_lock:
        if callback not in self.series_modified_callbacks:
            self.series_modified_callbacks.append(callback)
            logger.info(f"已注册回调函数: {callback.__name__}")

    def unregister_series_update_callback(self, callback):
        """取消注册回调函数"""
        with self.series_callback_lock:
            if callback in self.series_modified_callbacks:
                self.series_modified_callbacks.remove(callback)
                logger.info(f"已取消回调函数注册: {callback.__name__}")

    def _notify_callbacks(self, series_info):
        """通告所有已注册的回调函数"""
        with self.series_callback_lock:
            for callback in self.series_modified_callbacks:
                try:
                    callback(series_info)
                except Exception as e:
                    logger.error(f"回调函数执行失败: {e}", exc_info=True)

    def on_message(self, data):
        try:
            json_data = json.loads(data)
        except json.JSONDecodeError as e:
            logger.error(f"message JSON解析失败: {e}")
        logger.debug(f"收到消息: {data}")

    def on_error(self, e: Exception):
        """错误事件回调函数"""
        # 错误处理行为
        return

    def on_event(self, event_type, event_data):
        """订阅事件回调函数"""
        # 仅通知在 RefreshEventType 类型的事件
        if event_type in RefreshEventType:
            logger.info(f"捕获订阅事件 [{event_type}]:{event_data}")
            parsed_data = json.loads(event_data)
            # 在配置了KOMGA_LIBRARY_LIST时, 不通告 KOMGA_LIBRARY_LIST 外的库更改
            if parsed_data.get('libraryId') not in KOMGA_LIBRARY_LIST and len(KOMGA_LIBRARY_LIST) > 0:
                logger.info(
                    f"libraryId: {parsed_data.get('libraryId')} 不在 KOMGA_LIBRARY_LIST 中，跳过")
                return
            # 要不要在这里用多线程来 _notify_callbacks 呢?
            arg = {
                "event_type": event_type,
                "event_data": event_data
            }
            self._notify_callbacks(arg)
        else:
            logger.info(f"捕获无关事件 [{event_type}]:{event_data}")
