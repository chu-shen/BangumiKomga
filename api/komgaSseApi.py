# -*- coding: utf-8 -*- #
# ------------------------------------------------------------------
# Discussion: https://github.com/gotson/komga/discussions/1963
# Description: Komga SSE Service(https://github.com/gotson/komga/blob/0a2c3ace2883b5c9d8be4b5235a5b0db107eba5e/komga-webui/src/services/komga-sse.service.ts)
# ------------------------------------------------------------------


from config.config import KOMGA_BASE_URL, KOMGA_EMAIL, KOMGA_EMAIL_PASSWORD
import time
import json
from tools.log import logger
import requests
from requests.adapters import HTTPAdapter
from threading import Thread
import base64

# 可配置的订阅事件类型
RefreshEventType = ["SeriesAdded",
                    # 扫描库文件和扫描库文件(深度)两个选项会触发全库系列的SERIES_CHANGED事件
                    "SeriesChanged",
                    # 大量的 [TaskQueueStatus]: {"count":0,"countByType":{}} 触发
                    #  "TaskQueueStatus",
                    "BookAdded", "BookChanged", "BookImported"]


class KomgaSseClient:
    def __init__(self, base_url, username, password, api_key=None, timeout=30):
        self.url = base_url + "/sse/v1/events"
        self.auth = (username, password)
        self.running = False
        self.timeout = timeout
        self.thread = None

        # 用于Debug的默认回调函数
        self.on_open = lambda: logger.info("成功连接 Komga SSE 服务端点")
        self.on_error = lambda err: logger.info(f"出现错误: {err}")
        # TODO: 未实现默认消息回调
        self.on_message = lambda msg: logger.info(f"SSE消息内容: {msg}")
        # TODO: 未实现重试回调
        self.on_retry = lambda: logger.info("正在重连...")
        self.on_event = lambda event_type, data: logger.info(
            f"Event [{event_type}]: {data}")

        self.session = requests.Session()
        self.session.mount("http://", HTTPAdapter(max_retries=3))
        self.session.mount("https://", HTTPAdapter(max_retries=3))
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
        if api_key:
            self.session.headers["X-API-Key"] = api_key
            test_url = f"{base_url}/api/v2/users/me"
            response = self.session.get(test_url)

        else:
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
            try:
                response = self.session.get(
                    self.url,
                    stream=True,
                    timeout=self.timeout
                )
            except Exception as e:
                logger.error("Komga SSE 连接失败!")
                self.on_error(str(e))
                exit(1)
        if response.status_code != 200:
            logger.error("Komga: API Key 验证失败!")
            exit(1)

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

    def _connect(self):
        """建立 SSE 连接"""
        while self.running:
            try:
                with self.session.get(self.url,
                                      stream=True,
                                      timeout=self.timeout) as response:
                    if response.status_code != 200:
                        self.on_error(
                            f"HTTP {response.status_code}: {response.reason}")
                        return

                    self.on_open()
                    self._process_stream(response)

            except Exception as e:
                self.on_error(str(e))

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
                        # 重置为默认类型
                        current_event = "message"

    def _dispatch_event(self, event_type, data):
        """分发事件到对应处理器"""
        # 忽略refresh_event_type外的其他事件类型
        if event_type in RefreshEventType:
            self.on_event(event_type, data)


class KomgaSseApi:
    def __init__(self, base_url=KOMGA_BASE_URL, username=KOMGA_EMAIL, password=KOMGA_EMAIL_PASSWORD, api_key=None, timeout=30):
        # 实例化 KomgaSseApi 对象
        self.sse_client = KomgaSseClient(base_url, username, password)
        # 绑定回调
        self.sse_client.on_message = self.on_message
        self.sse_client.on_error = self.on_error
        self.sse_client.on_event = self.on_event
        # 启动 SSE 监听
        self._start_client()

    def _start_client(self):
        try:
            self.sse_client.start()
            while True:
                time.sleep(1)  # 保持主线程运行
        except KeyboardInterrupt:
            logger.warning("正在关闭SSE连接...")
            self.sse_client.stop()

    def on_message(self, data):
        try:
            json_data = json.loads(data)
            # 处理 JSON 数据
        except json.JSONDecodeError as e:
            logger.error("message JSON解析失败:", e)
        logger.info("普通消息:", json_data)

    # 错误事件回调函数
    def on_error(self, err):
        logger.error("错误消息:", err)

    # 订阅事件回调函数
    def on_event(self, event_type, data):
        if event_type in RefreshEventType:
            logger.debug(f"捕获订阅事件 [{event_type}]:", data)
            return {
                "event_type": event_type,
                "event_data": data
            }
        else:
            logger.debug(f"捕获其他事件 [{event_type}]:", data)
