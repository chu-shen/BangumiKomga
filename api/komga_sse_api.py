# -*- coding: utf-8 -*- #
# ------------------------------------------------------------------
# Discussion: https://github.com/gotson/komga/discussions/1963
# Description: Komga SSE Service(https://github.com/gotson/komga/blob/0a2c3ace2883b5c9d8be4b5235a5b0db107eba5e/komga-webui/src/services/komga-sse.service.ts)
# ------------------------------------------------------------------


import threading
import time
import json
import requests
import atexit
import base64
import datetime
from urllib3.util import Retry
from requests.adapters import HTTPAdapter
from threading import Thread, Lock
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from tools.log import logger
from config.config import KOMGA_BASE_URL, KOMGA_EMAIL, KOMGA_EMAIL_PASSWORD, KOMGA_LIBRARY_LIST


# 捕获线程内未处理异常，记录堆栈以便排查静默退出
try:
    def _thread_exc_handler(args):
        try:
            thread_name = getattr(args.thread, "name", "<unknown>")
            logger.exception(f"线程未捕获异常: {thread_name}", exc_info=(
                args.exc_type, args.exc_value, args.exc_traceback))
        except Exception:
            logger.exception("线程异常处理器自身出错")

    threading.excepthook = _thread_exc_handler
except Exception:
    # 在某些较老的 Python 版本上可能不存在 threading.excepthook
    pass

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
        # 基本设置
        self.base_url = base_url
        self.url = f"{base_url}/sse/v1/events"
        self.auth = (username, password)
        self.thread = None
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = retries

        # 连接状态管理
        # 使用 Event 作为线程安全的停止信号
        self._stop_event = threading.Event()
        # 记录当前活动的 Response 对象（用于在 stop() 时关闭以解除阻塞）
        self._current_response = None
        self.retry_count = 0
        self.delay = 1

        # 用于Debug的默认回调函数
        self.on_open = lambda: logger.info("成功连接 Komga SSE 服务端点")
        self.on_close = lambda: logger.info("正常关闭 Komga SSE 连接")
        self.on_error = lambda err: logger.error(f"出现错误: {err}", exc_info=True)
        self.on_message = lambda msg: logger.info(f"SSE消息内容: {msg}")
        self.on_retry = lambda: logger.info("正在重连...")
        self.on_event = lambda event_type, data: logger.info(
            f"Event [{event_type}]: {data}")

        self.session = self._create_session()
        self._setup_headers()

    def _create_session(self, pool_size=5) -> requests.Session:
        """创建带连接池和重试策略的会话"""
        session = requests.Session()
        retries = Retry(
            total=self.max_retries,
            backoff_factor=0.5,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["HEAD", "GET"]
        )
        adapter = HTTPAdapter(max_retries=retries,
                              pool_connections=pool_size,
                              pool_maxsize=pool_size)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        return session

    def _setup_headers(self):
        """设置请求头并验证身份"""
        headers = {
            # 客户端向服务器表明自身能够接收事件流格式数据的关键标识
            # 见MDN: https://developer.mozilla.org/zh-CN/docs/Web/API/Server-sent_events/Using_server-sent_events
            "Accept": "text/event-stream",
            "User-Agent": "chu-shen/BangumiKomga (https://github.com/chu-shen/BangumiKomga)",
            # 防止缓存干扰实时数据流
            "Cache-Control": "no-cache",
        }

        if self.api_key:
            headers["X-API-Key"] = self.api_key
            self.session.headers.update(headers)
            # 验证身份
            test_url = f"{self.base_url}/api/v2/users/me"
            response = None  # 提前声明变量
            try:
                response = self.session.get(test_url)
                if response.status_code != 200:
                    raise Exception(
                        f"Komga SSE API_KEY 验证失败: {response.status_code}")
            except requests.exceptions.RequestException as e:
                logger.error(f"API_KEY 身份验证失败: {e}")
                return
        elif self.auth:
            # 构建认证字符串
            credentials = f"{self.auth[0]}:{self.auth[1]}"
            encoded = base64.b64encode(
                credentials.encode("utf-8")).decode("utf-8")
            headers["Authorization"] = f"Basic {encoded}"
            self.session.headers.update(headers)
            response = None  # 提前声明变量
            # 测试连接
            try:
                response = self.session.get(
                    self.url,
                    stream=True,
                    timeout=self.timeout
                )
            # 防止取不到response.status_code
            except requests.exceptions.ConnectionError as e:
                logger.error(
                    f"Komga SSE 连接错误, HTTP {response.status_code}: {response.reason}, 错误: {e}", exc_info=True)
                return
            except Exception as e:
                logger.error(f"Komga SSE 连接错误: {e}")
                self.on_error(e)
                return
            if response.status_code != 200:
                logger.error("Komga 账户凭据验证失败!")
                return
        else:
            return

    def start(self):
        """启动 SSE 监听"""
        # 如果已有线程在运行，跳过重复启动
        if self.thread and self.thread.is_alive():
            return
        # 清除停止信号并启动线程
        self._stop_event.clear()
        self.thread = Thread(target=self._connect)
        self.thread.start()
        self.on_open()

    def stop(self):
        """停止 SSE 监听"""
        # 设置停止信号，关闭当前 response 以解除可能的阻塞读取
        self._stop_event.set()
        try:
            if self._current_response is not None:
                try:
                    self._current_response.close()
                except Exception:
                    pass
        finally:
            # 等待线程退出
            if self.thread:
                self.thread.join(timeout=5)
            # 释放 Session
            try:
                self.session.close()
            except Exception:
                pass
            self.on_close()

    def _connect(self):
        """建立 SSE 连接"""
        retry_count = 0
        while not self._stop_event.is_set():
            try:
                response = self.session.get(
                    self.url,
                    stream=True,
                    timeout=self.timeout
                )
                # 保留当前 response 以便外部 stop() 可关闭
                self._current_response = response
                with response:
                    if response.status_code != 200:
                        # 将非200视为连接错误，触发重连逻辑
                        raise requests.exceptions.RequestException(
                            f"Komga SSE 连接失败, HTTP {response.status_code}: {response.reason}")

                    self.on_open()
                    self._process_stream(response)
                    retry_count = 0  # 成功后重置重试计数
            except Exception as e:
                logger.error(f"Komga SSE 连接出错: {e}", exc_info=True)
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
            finally:
                # 无论如何都清理当前 response 引用，确保 stop() 后能释放资源
                try:
                    self._current_response = None
                except Exception:
                    pass

    def _parse_message_line(self, line, current_event, current_data):
        """事件行消息解析器"""
        if not line:
            # 空行表示事件结束, 分发事件
            self._dispatch_event(current_event, current_data)
            # 重置 current_event 和 current_data
            return "", ""
        # 解析事件类型
        if line.startswith("event:"):
            current_event = line[6:].strip()
        # 解析数据
        elif line.startswith("data:"):
            data_part = line[5:].strip()
            if current_data is None:
                current_data = data_part
            else:
                current_data += "\n" + data_part
        return current_event, current_data

    def _process_stream(self, response):
        """事件流解析器"""
        buffer = ""
        current_event = ""
        current_data = ""
        try:
            # iter_lines() 没有线程安全, 应配合 self.running 使用
            # https://tedboy.github.io/requests/generated/generated/requests.Response.iter_lines.html
            for line in response.iter_lines(decode_unicode=True):
                if self._stop_event.is_set():
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
                            current_event, current_data = self._parse_message_line(
                                line.strip(), current_event, current_data)
                    else:
                        # 空行表示事件分隔符
                        current_event, current_data = self._parse_message_line(
                            "", current_event, current_data)  # 触发事件分隔处理
                except Exception as e:
                    self.on_error(f"SSE 数据行 {line} 处理异常, {e}")
                    continue
        except requests.exceptions.RequestException as e:
            # 处理网络层异常（连接超时、断开等）
            self.on_error(f"读取 SSE 流数据时网络连接中断, {e}")

        except Exception as e:
            # 处理其他未知异常
            self.on_error(f"遇到未知错误, {e}")

    def _dispatch_event(self, event_type, data):
        """分发事件到对应处理器"""
        try:
            # 数据有效性验证
            if isinstance(data, str):
                json_data = json.loads(data)
            # 确保 json_data 是字典
            if not isinstance(json_data, dict):
                raise Exception(f"事件数据不是有效的JSON格式")
            # 事件过滤, 忽略refresh_event_type外的其他事件类型
            if event_type in RefreshEventType:
                self.on_event(event_type, json_data)
            else:
                self.on_message(json_data)
        except json.JSONDecodeError as e:
            self.on_error(f"事件数据的格式错误: {data}, {e}")
            return
        except Exception as e:
            self.on_error(f"事件 {event_type}, {data} 分发出错: {e}")
            return


class KomgaSseApi:
    def __init__(self, base_url=KOMGA_BASE_URL, username=KOMGA_EMAIL, password=KOMGA_EMAIL_PASSWORD, api_key=None, timeout=30, retries=5):
        # 实例化 KomgaSseApi 对象
        self.sse_client = KomgaSseClient(
            base_url, username, password, api_key, timeout, retries)

        self.series_modified_callbacks = []
        # 保护回调列表的互斥访问
        self.series_callback_lock = Lock()
        # 记录 series_id 最后刷新时间
        self.series_refresh_history = {}
        # 刷新间隔阈值
        self.refresh_interval = datetime.timedelta(seconds=20)

        # 绑定回调
        self.sse_client.on_message = self.on_message
        self.sse_client.on_error = self.on_error
        self.sse_client.on_event = self.on_event

        self.series_modified_callbacks = []
        # 使用守护线程启动SSE客户端，确保线程唯一性
        self.sse_thread = None
        self._start_sse_thread()
        # 使用线程池管理回调线程
        self.executor = ThreadPoolExecutor(max_workers=5)
        # 记录每个 series ID 的锁
        self.series_locks = {}
        # 程序退出时自动调用
        atexit.register(self._stop_client)
        # 启动 supervisor 以监控 sse_client 线程并在异常退出时有限次重启
        self._supervisor_stop = threading.Event()
        self._restart_attempts = 0
        self._restart_window_start = None
        self._supervisor_thread = None
        try:
            self._supervisor_thread = Thread(
                target=self._supervise, name="SSE_Supervisor", daemon=True)
            self._supervisor_thread.start()
        except Exception:
            logger.exception("启动 supervisor 线程失败")

    def _start_sse_thread(self):
        """确保 SSE 线程唯一且安全启动"""
        if self.sse_thread and self.sse_thread.is_alive():
            logger.warning("SSE 线程已运行，跳过重复启动")
            return
        # 启动监督线程（非守护），由主程序负责生命周期
        self.sse_thread = Thread(
            target=self._start_client,
            name="SSE_Client_Thread"
        )
        self.sse_thread.start()

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

    def _supervise(self):
        """监督 SSE 客户端线程，发现非预期退出时有限次重启"""
        MAX_ATTEMPTS = 5
        WINDOW_SECONDS = 600
        CHECK_INTERVAL = 10
        while not self._supervisor_stop.is_set():
            try:
                client_thread = getattr(self.sse_client, 'thread', None)
                client_stopped = getattr(self.sse_client, '_stop_event', None)
                stopped = False
                if client_stopped is not None and client_stopped.is_set():
                    stopped = True
                if (client_thread is None or not client_thread.is_alive()) and not stopped:
                    now = time.time()
                    if self._restart_window_start is None or now - self._restart_window_start > WINDOW_SECONDS:
                        self._restart_window_start = now
                        self._restart_attempts = 0
                    if self._restart_attempts < MAX_ATTEMPTS:
                        logger.warning(
                            "检测到 SSE 客户端线程异常退出，尝试重启（attempt %s）", self._restart_attempts + 1)
                        try:
                            self._restart_attempts += 1
                            self._restart_sse_client()
                        except Exception:
                            logger.exception("重启 SSE 客户端时出错")
                    else:
                        logger.critical("SSE 客户端在窗口期内重启次数过多，停止尝试并等待人工干预")
                        break
                time.sleep(CHECK_INTERVAL)
            except Exception:
                logger.exception("监督线程异常")
                time.sleep(CHECK_INTERVAL)

    def _stop_client(self):
        # 停止 SSE 客户端（使用其 stop() 方法保证资源被正确释放）
        try:
            self.sse_client.stop()
        except Exception:
            logger.exception("停止 SSE 客户端时出错")

        # 等待SSE线程结束
        if self.sse_client.thread and self.sse_client.thread.is_alive():
            self.sse_client.thread.join(timeout=5)

        # 停止 supervisor
        try:
            if getattr(self, '_supervisor_stop', None) is not None:
                self._supervisor_stop.set()
            if getattr(self, '_supervisor_thread', None) and self._supervisor_thread.is_alive():
                self._supervisor_thread.join(timeout=2)
        except Exception:
            logger.exception("停止 supervisor 线程时出错")

        # 关闭线程池
        # 先尝试非阻塞关闭，再等待有限时间
        self.executor.shutdown(wait=False)
        # 等待最多5秒让任务完成
        try:
            # Python 3.9+ 支持 timeout 参数
            if hasattr(self.executor, 'shutdown') and 'timeout' in self.executor.shutdown.__code__.co_varnames:
                self.executor.shutdown(wait=True, timeout=5)
            else:
                # 降级处理：等待所有任务完成（阻塞直到完成或手动中断）
                self.executor.shutdown(wait=True)
        except Exception:
            logger.warning(
                "ThreadPoolExecutor 关闭超时，可能存在长时间运行的任务", exc_info=True)
        logger.info("SSE 客户端和线程池已关闭")

    def register_series_update_callback(self, callback):
        """注册系列更新回调函数"""
        with self.series_callback_lock:
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
        series_id = series_info['event_data'].get('seriesId')
        if not series_id:
            return

        now = datetime.datetime.now()
        with self._get_series_lock(series_id):
            # 检查刷新间隔
            for callback in list(self.series_modified_callbacks):
                if series_id in self.series_refresh_history:
                    last_time = self.series_refresh_history[series_id]
                    if now - last_time < self.refresh_interval:
                        logger.debug(f"{series_id} 已在 {last_time} 刷新，跳过重复请求")
                        return
                try:
                    # 更新时间戳并执行刷新
                    self.series_refresh_history[series_id] = now
                    # 提交任务到线程池
                    future = self.executor.submit(callback, series_info)
                    # 添加回调以记录任务完成或异常

                    def _log_result(future):
                        try:
                            future.result()
                        except Exception as e:
                            logger.exception(
                                "回调任务执行异常: %s", callback.__name__, exc_info=True)
                    future.add_done_callback(_log_result)
                except Exception as e:
                    logger.exception("提交回调任务时出错", exc_info=True)
                    self.on_error(e)

    def _restart_sse_client(self):
        """安全重启SSE客户端"""
        try:
            self.sse_client.stop()
            time.sleep(2)  # 等待2秒后重启
            self.sse_client.start()
        except Exception as e:
            logger.critical("重启SSE客户端失败", exc_info=True)

    # 为每个 series_id 提供一个独立的锁对象, lru_cache 会根据传入的参数来缓存不同的结果
    # 300是随手填的, 非经验最优值
    @lru_cache(maxsize=300)
    def _get_series_lock(self, series_id):
        return threading.Lock()

    def on_message(self, data):
        logger.debug(f"收到非订阅 SSE 消息: {data}")

    def on_error(self, e: Exception):
        """错误事件回调函数"""
        # 错误处理行为
        logger.error(f"遇到 SSE 错误: {e} ", exc_info=True)
        # 错误自动重连
        if "connection" in str(e).lower():
            self._restart_sse_client()

    def on_event(self, event_type, event_data):
        """订阅事件回调函数"""
        # 仅通知在 RefreshEventType 类型的事件
        if event_type in RefreshEventType:
            logger.debug(f"捕获订阅事件 [{event_type}]:{event_data}")
            library_id = event_data.get("libraryId")
            # 判断 KOMGA_LIBRARY_LIST 是否为空
            if not KOMGA_LIBRARY_LIST:
                pass
            # 在配置了KOMGA_LIBRARY_LIST时, 不通告 KOMGA_LIBRARY_LIST 外的库更改
            elif not any(library_id == lib["LIBRARY"] for lib in KOMGA_LIBRARY_LIST):
                logger.info(
                    f"libraryId: {library_id} 不在 KOMGA_LIBRARY_LIST 中，跳过")
                return
            # 要不要在这里用多线程来执行 _notify_callbacks 呢?
            arg = {"event_type": event_type, "event_data": event_data}
            self._notify_callbacks(arg)
        else:
            logger.debug(f"捕获无关事件 [{event_type}]:{event_data}")
