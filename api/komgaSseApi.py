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
        self._current_event = ""
        self._current_data = ""

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
            try:
                response = self.session.get(test_url)
                if response.status_code != 200:
                    raise Exception(
                        f"Komga SSE API_KEY 验证失败: {response.status_code}")
            except requests.exceptions.RequestException as e:
                logger.error(f"API_KEY 身份验证失败: {e}")
                return
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
            # 防止取不到response.status_code
            except requests.exceptions.ConnectionError as e:
                logger.error(f"Komga SSE 连接错误: {e}")
            except Exception as e:
                logger.error(
                    f"Komga SSE HTTP错误, HTTP {response.status_code}: {response.reason}")
                self.on_error(e)
                exit(1)
            if response.status_code != 200:
                logger.error("Komga 账户凭据验证失败!")
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

    def _parse_message_line(self, line):
        """事件行消息解析器"""
        if not line:
            # 空行表示事件结束, 分发事件
            self._dispatch_event(self._current_event, self._current_data)
            self._current_event = ""
            self._current_data = ""
            return
        # 解析事件类型
        if line.startswith("event:"):
            self._current_event = line[6:].strip()
        # 解析数据
        elif line.startswith("data:"):
            data_part = line[5:].strip()
            if self._current_data is None:
                self._current_data = data_part
            else:
                # 处理多行data
                self._current_data += "\n" + data_part

    def _process_stream(self, response):
        """事件流解析器"""
        buffer = ""
        try:
            # iter_lines() 没有线程安全, 应配合 self.running 使用
            # https://tedboy.github.io/requests/generated/generated/requests.Response.iter_lines.html
            for line in response.iter_lines(decode_unicode=True):
                if not self.running:
                    break
                try:
                    # 非空行
                    if line:
                        # 处理可能的多行数据
                        buffer += line + "\n"  # 确保每行以换行符结尾
                        # 分割完整行（以换行符结束）
                        lines = buffer.split("\n")
                        # 保留最后一个未完成的行（如果有的话）
                        if lines and lines[-1] == "":  # 完整行结束
                            buffer = ""
                            lines = lines[:-1]
                        else:
                            buffer = lines[-1]  # 保留未完成行
                            lines = lines[:-1]
                        # 处理所有完整行
                        for line in lines:
                            self._parse_message_line(line.strip())
                    else:
                        # 空行表示事件分隔符
                        self._parse_message_line("")  # 触发事件分隔处理
                except Exception as e:
                    self.on_error(f"SSE数据行 {line} 处理异常, {e}")
                    continue
        except requests.exceptions.RequestException as re:
            # 处理网络层异常（连接超时、断开等）
            self.on_error(f"网络连接中断, {e}")

        except Exception as e:
            # 处理其他未知异常
            self.on_error(f"系统级错误, {e}")

    def _dispatch_event(self, event_type, data):
        """分发事件到对应处理器"""
        try:
            # 数据有效性验证
            if isinstance(data, str):
                data = json.loads(data)
            # 忽略refresh_event_type外的其他事件类型
            if event_type in RefreshEventType:
                self.on_event(event_type, data)
            else:
                self.on_message(data)
        except json.JSONDecodeError as e:
            self.on_error("事件数据的JSON格式无效", raw_data=data)
            return
        except Exception as e:
            self.on_error("事件分发出错", error=e)
            return


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
            # 改为依赖主线程的保持
            self.sse_client.start()
        except KeyboardInterrupt:
            logger.warning("正在关闭SSE连接...")
            self.sse_client.stop()
        except Exception as e:
            logger.error(f"启动SSE客户端失败: {e}")
            self.sse_client.stop()

    def register_series_update_callback(self, callback):
        """注册系列更新回调函数"""
        # with self.series_callback_lock:
        if callback not in self.series_modified_callbacks:
            self.series_modified_callbacks.append(callback)
            logger.debug(f"已注册回调函数: {callback.__name__}")

    def unregister_series_update_callback(self, callback):
        """取消注册回调函数"""
        with self.series_callback_lock:
            if callback in self.series_modified_callbacks:
                self.series_modified_callbacks.remove(callback)
                logger.debug(f"已取消回调函数注册: {callback.__name__}")

    def _notify_callbacks(self, series_info):
        """通告所有已注册的回调函数"""
        with self.series_callback_lock:
            for callback in self.series_modified_callbacks:
                try:
                    # 将回调函数放在独立线程中执行, 避免阻塞事件处理
                    Thread(target=callback, args=(
                        series_info,), daemon=True).start()
                except Exception as e:
                    self.on_error(e)

    def on_message(self, data):
        logger.debug(f"收到非订阅 SSE 消息: {data}")

    def on_error(self, e: Exception):
        """错误事件回调函数"""
        # 错误处理行为
        logger.error(f"遇到 SSE 错误: {e} ", exc_info=True)
        return

    def on_event(self, event_type, event_data):
        """订阅事件回调函数"""
        # 仅通知在 RefreshEventType 类型的事件
        if event_type in RefreshEventType:
            logger.debug(f"捕获订阅事件 [{event_type}]:{event_data}")
            # 判断 KOMGA_LIBRARY_LIST 是否为空
            if not KOMGA_LIBRARY_LIST:
                pass
            # 在配置了KOMGA_LIBRARY_LIST时, 不通告 KOMGA_LIBRARY_LIST 外的库更改
            elif event_data.get('libraryId') not in KOMGA_LIBRARY_LIST:
                logger.info(
                    f"libraryId: {event_data.get('libraryId')} 不在 KOMGA_LIBRARY_LIST 中，跳过")
                return
            # 要不要在这里用多线程来 _notify_callbacks 呢?
            arg = {
                "event_type": event_type,
                "event_data": event_data
            }
            self._notify_callbacks(arg)
        else:
            logger.debug(f"捕获无关事件 [{event_type}]:{event_data}")
