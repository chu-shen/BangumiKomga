import unittest
from unittest.mock import MagicMock, patch
import json
import threading
import time
from api.komgaSseApi import KomgaSseClient, KomgaSseApi, RefreshEventType


class TestKomgaSseClient(unittest.TestCase):
    """基于Mock的Komga SSE测试"""

    def setUp(self):
        # 模拟配置
        self.base_url = "http://mocked-komga-url"
        self.username = "test_user"
        self.password = "test_password"

        # 模拟requests.post，防止真实认证请求
        self.mock_post_patcher = patch('requests.post')
        self.mock_post = self.mock_post_patcher.start()

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
            # 完整事件块
            'event: SeriesAdded\ndata: {"id":"series1", "libraryId":"lib1"}\n\n',
            # 多行数据事件
            'event: BookAdded\ndata: {"id":"book1", "seriesId":"series1"}\n'
            'data: {"extra":"continued"}\n\n',
            # 不完整数据块
            'event: SeriesChanged\ndata: {"id":"series2"',
            # 继续的数据块
            'data: "libraryId":"lib1"}\n\n',
            # 无效事件类型
            'event: UnknownEvent\ndata: {"test":true}\n\n'
        ]
        # 模拟真实字节流传输
        self.test_event_bytes = [event.encode(
            'utf-8') for event in self.test_events]
        self.response_mock.iter_content.side_effect = lambda chunk_size, decode_unicode: iter(
            self.test_event_bytes)

        # 创建不会发起真实请求的测试客户端
        self.client = KomgaSseClient(
            self.base_url, self.username, self.password)

    def tearDown(self):
        patch.stopall()

    def test_full_sse_client_lifecycle(self):
        """模拟测试完整的SSE Client生命周期"""
        # 创建客户端
        client = KomgaSseClient(
            self.base_url, self.username, self.password,
            timeout=5, retries=2
        )

        # 设置事件处理回调
        received_events = []

        def mock_callback(event_type, data):
            received_events.append((event_type, data))

        client.on_event = mock_callback

        # 模拟连接过程
        def simulate_stream():
            client._process_stream(self.response_mock)

        # 启动模拟流处理
        stream_thread = threading.Thread(target=simulate_stream)
        client.running = True
        stream_thread.start()

        # 等待处理完成
        time.sleep(1)
        client.running = False
        stream_thread.join(timeout=2)

        # 验证接收到的事件
        self.assertEqual(len(received_events), 5)

        # 验证事件解析正确性
        self.assertEqual(received_events[0][0], "SeriesAdded")
        self.assertIn("series1", received_events[0][1])

        # 验证多行数据合并
        self.assertEqual(received_events[1][0], "BookAdded")
        self.assertIn("continued", received_events[1][1])

        # 验证不完整数据处理
        self.assertEqual(received_events[2][0], "SeriesChanged")
        self.assertIn("series2", received_events[2][1])

        # 验证无效事件处理
        self.assertEqual(received_events[4][0], "UnknownEvent")

    def test_authentication_flow(self):
        """模拟测试认证流程"""
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
        """测试重连逻辑（模拟异常）"""
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


@unittest.skip("临时跳过测试")
class TestKomgaSseApi(unittest.TestCase):
    def setUp(self):
        # 模拟配置
        self.base_url = "http://mocked-komga-url"
        self.username = "test_user"
        self.password = "test_password"

        # 模拟requests.post，防止真实认证请求
        self.mock_post_patcher = patch('requests.post')
        self.mock_post = self.mock_post_patcher.start()

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
            # 完整事件块
            'event: SeriesAdded\ndata: {"id":"series1", "libraryId":"lib1"}\n\n',
            # 多行数据事件
            'event: BookAdded\ndata: {"id":"book1", "seriesId":"series1"}\n'
            'data: {"extra":"continued"}\n\n',
            # 不完整数据块
            'event: SeriesChanged\ndata: {"id":"series2"',
            # 继续的数据块
            'data: "libraryId":"lib1"}\n\n',
            # 无效事件类型
            'event: UnknownEvent\ndata: {"test":true}\n\n'
        ]

        # 模拟真实字节流传输
        self.test_event_bytes = [event.encode(
            'utf-8') for event in self.test_events]
        self.response_mock.iter_content.side_effect = lambda chunk_size, decode_unicode: iter(
            self.test_event_bytes)

        # 创建不会发起真实请求的API实例
        self.api = KomgaSseApi(
            self.base_url, self.username, self.password)

    def test_event_filtering_and_dispatching(self):
        """测试事件过滤与分发逻辑"""
        test_api = self.api
        # 准备测试回调
        callback_data = []

        def test_callback(data):
            callback_data.append(data)

        # 注册
        test_api.register_series_update_callback(test_callback)

        # 测试允许的事件类型
        for event_type in RefreshEventType:
            with self.subTest(event_type=event_type):
                test_data = json.dumps({"libraryId": "lib1"})
                test_api.on_event(event_type, test_data)
                self.assertTrue(len(callback_data) > 0)
                callback_data.clear()

        # 测试库过滤（匹配）
        with patch('config.config.KOMGA_LIBRARY_LIST', ["lib1"]):
            test_api.on_event("SeriesAdded", json.dumps({"libraryId": "lib1"}))
            self.assertEqual(len(callback_data), 1)

        # 测试库过滤（不匹配）
        callback_data.clear()
        with patch('config.config.KOMGA_LIBRARY_LIST', ["lib2"]):
            test_api.on_event("SeriesAdded", json.dumps({"libraryId": "lib1"}))
            self.assertEqual(len(callback_data), 0)

    pass


@unittest.skip("临时跳过测试")
class TestErrorHandling(unittest.TestCase):
    """错误处理测试"""

    def setUp(self):
        # 模拟配置
        self.base_url = "http://mocked-komga-url"
        self.username = "test_user"
        self.password = "test_password"

        # 模拟requests.post，防止真实认证请求
        self.mock_post_patcher = patch('requests.post')
        self.mock_post = self.mock_post_patcher.start()

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

        # 模拟真实字节流传输
        self.test_event_bytes = [event.encode(
            'utf-8') for event in self.test_events]
        self.response_mock.iter_content.side_effect = lambda chunk_size, decode_unicode: iter(
            self.test_event_bytes)

        # 创建不会发起真实请求的测试客户端
        self.client = KomgaSseClient(
            self.base_url, self.username, self.password)

    def test_invalid_json_handling(self):
        """测试无效JSON数据处理"""

        # 模拟无效JSON数据
        invalid_data = '{"invalid": true'
        with patch.object(self.client, 'on_error') as error_mock:
            self.client._dispatch_event("SeriesAdded", invalid_data)
            self.assertTrue(error_mock.called)

    def test_network_errors(self):
        """测试网络错误处理"""
        # 模拟网络错误
        self.response_mock.iter_content.side_effect = Exception(
            "Network error")

        with patch.object(self.client, 'on_error') as error_mock:
            self.client._process_stream(self.response_mock)
            self.assertTrue(error_mock.called)
