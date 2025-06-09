import unittest
from unittest.mock import MagicMock, patch, call
from api.komga_sse_api import KomgaSseClient, KomgaSseApi


# @unittest.skip("临时跳过测试")
class TestKomgaSseClient(unittest.TestCase):
    """基于Mock的Komga SSE测试"""

    def setUp(self):
        # 模拟配置
        self.base_url = "http://mocked-komga-url"
        self.username = "test_user"
        self.password = "test_password"

        # 模拟requests.get，防止真实认证请求
        self.mock_get_patcher = patch('requests.get')
        self.mock_get = self.mock_get_patcher.start()

        # 模拟日志系统
        self.mock_logger = MagicMock()
        patch('tools.log.logger', self.mock_logger).start()

        # 模拟requests.Session
        self.session_mock = MagicMock()
        self.session_mock.headers = {}
        self.session_constructor = patch(
            'requests.Session', return_value=self.session_mock).start()

        # 模拟Response对象
        self.response_mock = MagicMock()
        self.response_mock.status_code = 200
        self.response_mock.headers = {}
        self.session_mock.get.return_value = self.response_mock

        # 准备测试事件数据
        self.test_events = [
            # 单行事件块
            'event: SeriesAdded\ndata: {"id":"series1", "libraryId":"0JR3B78BEGVYG"}\n\n',
            # 多行数据事件
            'event: BookAdded\ndata: {"id":"book1", "seriesId":"series1"}\n'
            'data: {"libraryId":"0JR3B78BEGVYG"}\n\n',
            # 不完整数据块
            'event: SeriesChanged\ndata: {"id":"series2"',
            # 多行数据中的后继数据块
            'data: {"libraryId":"0JR3B78BEGVYG"}\n\n',
            # 无效事件类型
            'event: UnknownEvent\ndata: {"test":true}\n\n'
        ]
        # 模拟真实字节流传输
        self.test_event_bytes = [event.encode(
            'utf-8') for event in self.test_events]
        self.response_mock.iter_lines.side_effect = lambda chunk_size, decode_unicode: iter(
            self.test_event_bytes)

        # 创建不会发起真实请求的测试客户端
        self.client = KomgaSseClient(
            self.base_url, self.username, self.password)

    def tearDown(self):
        patch.stopall()

    def test_authentication_flow(self):
        """测试SSE Client - 模拟认证流程"""
        # 测试API Key认证
        api_key_client = KomgaSseClient(
            self.base_url, self.username, self.password,
            api_key="test_key"
        )
        headers = api_key_client.session.headers
        self.assertEqual(headers["X-API-Key"], "test_key")

        # 验证 API Key 认证时请求了 `/api/v2/users/me`
        test_url = f"{self.base_url}/api/v2/users/me"
        api_key_client.session.get.assert_any_call(test_url)

        # 测试Basic认证
        basic_client = KomgaSseClient(
            self.base_url, self.username, self.password
        )
        auth_header = basic_client.session.headers.get("Authorization", "")
        self.assertTrue(auth_header.startswith("Basic "))

        # 验证 Basic 认证时请求了 `/sse/v1/events` 且带有 stream=True 和 timeout=30
        expected_url = f"{self.base_url}/sse/v1/events"
        basic_client.session.get.assert_any_call(
            expected_url,
            stream=True,
            timeout=30
        )

    def test_reconnection_logic(self):
        """测试SSE Client - 模拟异常重连逻辑"""
        # 创建客户端
        client = KomgaSseClient(
            self.base_url, self.username, self.password,
            timeout=1, retries=2
        )

        # 模拟连接失败
        self.session_mock.get.side_effect = [
            Exception("Connection failed")] * 3

        # 模拟连接循环
        with patch('time.sleep') as sleep_mock:
            with patch.object(client, 'start') as connect_mock:
                client.running = True
                client._connect()

                # 验证重试次数
                self.assertLessEqual(connect_mock.call_count, 2)
                # 验证延迟调用
                self.assertTrue(sleep_mock.called)

    def test_invalid_json_handling(self):
        """测试SSE Client - 无效JSON数据处理"""

        # 模拟无效JSON数据
        invalid_data = '{"invalid": true'
        with patch.object(self.client, 'on_error') as error_mock:
            self.client._dispatch_event("SeriesAdded", invalid_data)
            self.assertTrue(error_mock.called)

    def test_network_errors(self):
        """测试SSE Client - 网络错误处理"""
        # 模拟网络错误
        # _process_stream 使用 response.iter_lines() 读取行数据
        # 因此要用 response_mock.iter_lines.side_effect 来模拟异常
        self.response_mock.iter_lines.side_effect = Exception("Network error")

        with patch.object(self.client, 'on_error') as error_mock:
            self.client._process_stream(self.response_mock)
            self.assertTrue(error_mock.called)

    def test_multi_line_event_processing(self):
        """测试SSE Client - 多行事件数据拼接处理"""
        import json
        sse_lines = [
            # 单行数据
            "event: SeriesAdded",
            "data: {\"libraryId\": \"lib1\", \"seriesId\": \"s1\"}",
            "",
            # 多行数据
            "event: BookAdded",
            "data: {\"seriesId\": \"s1\", \"bookId\": \"b1\", ",
            "data: \"title\": \"Chapter 1\"}",
            "",
            # 不应在该函数中处理错误
            # # 不完整的多行数据
            # "data: {\"libraryId\": \"lib2\", \"seriesId\": \"s2\",",
            # "data: \"name\": \"Another Ser\"",
            # "",
        ]

        expected_calls = [
            ("SeriesAdded", {"libraryId": "lib1", "seriesId": "s1"}),
            ("BookAdded", {"seriesId": "s1",
             "bookId": "b1", "title": "Chapter 1"}),
            # ("", {"libraryId": "lib2", "seriesId": "s2", "name": "Another Series"})
        ]

        # 模拟SSE流
        def _simulate_sse_stream(lines): return type(
            'MockResponse', (), {'iter_lines': lambda _, **__: iter(lines)})()

        # 开始处理SSE流
        with patch.object(KomgaSseClient, '_dispatch_event', new_callable=MagicMock):
            self.client.running = True
            self.client._process_stream(_simulate_sse_stream(sse_lines))

            # 验证多行事件数据处理结果
            self.assertEqual(self.client._dispatch_event.call_count, 2)
            for i, (event, data) in enumerate(expected_calls):
                call_args = self.client._dispatch_event.call_args_list[i]
                self.assertEqual(call_args[0][0], event)
                self.assertEqual(json.loads(call_args[0][1]), data)

    def test_unicode_decoding_error(self):
        """测试SSE Client - Unicode解码错误处理"""
        # 创建包含非法字符的数据
        invalid_bytes = b'event: ErrorTest\ndata: {"invalid": "\x80"}\n\n'

        # 配置模拟
        self.response_mock.iter_lines.return_value = [invalid_bytes]

        # 执行测试
        with patch.object(self.client, 'on_error') as error_mock:
            with patch('builtins.print'):
                self.client._process_stream(self.response_mock)
                self.assertTrue(error_mock.called)

    def test_retry_logic_with_different_exceptions(self):
        """测试SSE Client - 不同异常类型下的重试行为"""
        import requests
        test_exceptions = [
            requests.exceptions.Timeout,
            requests.exceptions.ConnectionError,
            requests.exceptions.HTTPError,
        ]

        for exc_type in test_exceptions:
            with self.subTest(exception=exc_type):
                client = KomgaSseClient(
                    self.base_url, self.username, self.password,
                    retries=2, timeout=1
                )
                # 构建异常实例

                def make_exception(*args, **kwargs):
                    exc = exc_type()
                    exc.response = type('obj', (object,), {})
                    return exc

                # 模拟异常
                self.session_mock.get.side_effect = [
                    make_exception() for _ in range(3)]

                # 开始模拟连接
                with patch('time.sleep') as sleep_mock:
                    with patch.object(client, 'start') as connect_mock:
                        client.running = True
                        client._connect()

                        # 验证重试次数
                        self.assertLessEqual(connect_mock.call_count, 2)
                        self.assertLessEqual(
                            client.retry_count, client.max_retries)
                        # 验证等待
                        self.assertTrue(sleep_mock.called)

    def test_exponential_backoff_algorithm(self):
        """测试SSE Client - 指数退避算法准确性"""
        import requests
        client = KomgaSseClient(
            self.base_url, self.username, self.password,
            retries=5, timeout=1
        )

        # 模拟持续超时
        self.session_mock.get.side_effect = requests.exceptions.Timeout

        with patch('time.sleep') as sleep_mock:
            with patch.object(client, 'start') as connect_mock:
                client.running = True
                client._connect()

                # 验证延迟序列 [2, 4, 8, 16, 30]
                calls = [call(2), call(
                    4), call(8), call(16), call(30)]
                sleep_mock.assert_has_calls(calls)

# @unittest.skip("临时跳过测试")


class TestKomgaSseApi(unittest.TestCase):
    def setUp(self):
        # 模拟配置
        self.base_url = "http://mocked-komga-url"
        self.username = "test_user"
        self.password = "test_password"

        # 模拟requests.get，防止真实认证请求
        self.mock_get_patcher = patch('requests.get')
        self.mock_get = self.mock_get_patcher.start()

        # 模拟日志系统
        self.mock_logger = MagicMock()
        patch('tools.log.logger', self.mock_logger).start()

        # 模拟requests.Session
        self.session_mock = MagicMock()
        self.session_constructor = patch(
            'requests.Session', return_value=self.session_mock).start()

        # 模拟Response对象
        self.response_mock = MagicMock()
        self.response_mock.status_code = 200
        self.response_mock.headers = {}
        self.session_mock.get.return_value = self.response_mock

        # 准备测试事件数据
        self.test_events = [
            # 单行事件块
            'event: SeriesAdded\ndata: {"id":"series1", "libraryId":"0JR3B78BEGVYG"}\n\n',
            # 多行数据事件
            'event: BookAdded\ndata: {"id":"book1", "seriesId":"series1"}\n'
            'data: {"libraryId":"0JR3B78BEGVYG"}\n\n',
            # 不完整数据块
            'event: SeriesChanged\ndata: {"id":"series2"',
            # 多行数据中的后继数据块
            'data: {"libraryId":"0JR3B78BEGVYG"}\n\n',
            # 无效事件类型
            'event: UnknownEvent\ndata: {"test":true}\n\n'
        ]

        # 模拟真实字节流传输
        self.test_event_bytes = [event.encode(
            'utf-8') for event in self.test_events]
        self.response_mock.iter_lines.side_effect = lambda chunk_size, decode_unicode: iter(
            self.test_event_bytes)

        # 创建不会发起真实请求的API实例
        self.api = KomgaSseApi(
            self.base_url, self.username, self.password)

    # 应特别注意, 以:
    # from config.config import KOMGA_LIBRARY_LIST 方式导入的变量将作为本地变量绑定到当前模块的命名空间
    # 不能再使用:
    # patch('config.config.KOMGA_LIBRARY_LIST', new=[])
    # 而应该使用:
    # patch('api.komga_sse_api.KOMGA_LIBRARY_LIST', new=[])

    def test_library_filtering_with_empty_list(self):
        """测试SSE API - 空KOMGA_LIBRARY_LIST时的事件分发逻辑"""
        with patch('api.komga_sse_api.KOMGA_LIBRARY_LIST', new=[]):
            api = self.api
            callback_data = []

            def test_callback(data):
                callback_data.append(data)

            api.register_series_update_callback(test_callback)
            api.on_event("SeriesAdded", {
                         "seriesId": "series1", "libraryId": "lib1"})
            self.assertEqual(len(callback_data), 1)

    def test_library_filtering_with_matching_id(self):
        """测试SSE API - 匹配KOMGA_LIBRARY_LIST时的事件分发逻辑"""
        with patch('api.komga_sse_api.KOMGA_LIBRARY_LIST', new=['lib1']):
            api = self.api
            callback_data = []

            def test_callback(data):
                callback_data.append(data)

            api.register_series_update_callback(test_callback)
            api.on_event("SeriesAdded", {
                         "seriesId": "series1", "libraryId": "lib1"})
            self.assertEqual(len(callback_data), 1)

    def test_library_filtering_with_non_matching_id(self):
        """测试SSE API - 不匹配KOMGA_LIBRARY_LIST时的事件分发逻辑"""
        with patch('api.komga_sse_api.KOMGA_LIBRARY_LIST', new=['lib2']):
            api = self.api
            callback_data = []

            def test_callback(data):
                callback_data.append(data)

            api.register_series_update_callback(test_callback)
            api.on_event("SeriesAdded", {
                         "seriesId": "series1", "libraryId": "lib1"})
            self.assertEqual(len(callback_data), 0)

    def test_concurrent_callback_registration(self):
        """测试SSE API - 注册/注销回调"""
        # 创建测试回调
        def callback1(x): return None
        def callback2(x): return None

        # 模拟并发操作
        # 注册
        self.api.register_series_update_callback(callback1)
        self.api.register_series_update_callback(callback2)

        # 验证回调注册
        self.assertIn(callback1, self.api.series_modified_callbacks)
        # 注销
        self.api.unregister_series_update_callback(callback1)
        self.api.unregister_series_update_callback(callback2)

        # 验证回调注销
        self.assertNotIn(callback1, self.api.series_modified_callbacks)
        self.assertNotIn(callback2, self.api.series_modified_callbacks)

    def test_series_lock_cache_behavior(self):
        """测试SSE API - 系列锁缓存行为"""
        # 获取多个锁
        lock1 = self.api._get_series_lock("series1")
        lock2 = self.api._get_series_lock("series2")
        lock3 = self.api._get_series_lock("series1")  # 相同ID

        # 验证缓存行为
        self.assertIsNotNone(lock1)
        self.assertIsNotNone(lock2)
        self.assertIs(lock1, lock3)  # 相同ID应返回相同锁

    def test_event_callback_thread_pool(self):
        """测试SSE API - 回调线程池行为"""
        # 准备测试数据
        event_data = {
            "event_type": "SeriesAdded",
            "event_data": {"seriesId": "series1", "libraryId": "lib1"}
        }
        # 创建测试回调
        def callback_test(x): return None
        # 执行回调
        with patch.object(self.api.executor, 'submit', new=MagicMock()) as mock_submit:
            self.api.register_series_update_callback(callback_test)
            self.api._notify_callbacks(event_data)
            self.assertTrue(mock_submit.called)

    def test_session_closing_behavior(self):
        """测试SSE API - Session关闭状态"""
        client = KomgaSseClient(
            self.base_url, self.username, self.password
        )

        # 模拟关闭
        client.stop()

        # 验证session关闭
        self.session_mock.close.assert_called_once()
