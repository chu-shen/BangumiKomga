import unittest
from unittest.mock import MagicMock, patch, call
import json
import threading
import time
from config.config import KOMGA_BASE_URL, KOMGA_EMAIL, KOMGA_EMAIL_PASSWORD
from api.komgaSseApi import KomgaSseClient, KomgaSseApi, RefreshEventType


class TestKomgaIntegration(unittest.TestCase):
    """基于Mock的Komga SSE测试"""

    def setUp(self):
        # 模拟配置, 与config.template.py内容一致
        self.base_url = KOMGA_BASE_URL
        self.username = KOMGA_EMAIL
        self.password = KOMGA_EMAIL_PASSWORD

        # 模拟日志系统
        self.mock_logger = MagicMock()
        patch('sse_client.logger', self.mock_logger).start()

        # 模拟requests.Session
        self.session_mock = MagicMock()
        self.session_constructor = patch(
            'sse_client.requests.Session', return_value=self.session_mock).start()

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

        # 设置迭代器返回值
        self.response_mock.iter_content.side_effect = lambda chunk_size, decode_unicode: iter(
            self.test_events)

    def tearDown(self):
        patch.stopall()

    def test_full_sse_lifecycle(self):
        """模拟测试完整的SSE生命周期"""
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
        self.assertIn("X-API-Key", headers)
        self.assertEqual(headers["X-API-Key"], "test_key")

        # 测试Basic认证
        basic_client = KomgaSseClient(
            self.base_url, self.username, self.password
        )
        auth_header = basic_client.session.headers.get("Authorization", "")
        self.assertTrue(auth_header.startswith("Basic "))

        # 验证认证方式选择
        test_url = f"{self.base_url}/api/v2/users/me"
        api_key_client.session.get.assert_called_with(test_url)
        basic_client.session.get.assert_called_with(
            api_key_client.url, stream=True, timeout=30
        )

    def test_event_filtering_and_dispatching(self):
        """测试事件过滤与分发逻辑"""
        # 创建测试API实例
        test_api = KomgaSseApi(
            self.base_url, self.username, self.password
        )

        # 准备测试回调
        callback_data = []

        def test_callback(data):
            callback_data.append(data)

        test_api.register_series_update_callback(test_callback)

        # 测试允许的事件类型
        for event_type in RefreshEventType:
            with self.subTest(event_type=event_type):
                test_data = json.dumps({"libraryId": "lib1"})
                test_api.on_event(event_type, test_data)
                self.assertTrue(len(callback_data) > 0)
                callback_data.clear()

        # 测试库过滤（匹配）
        with patch('sse_client.KOMGA_LIBRARY_LIST', ["lib1"]):
            test_api.on_event("SeriesAdded", json.dumps({"libraryId": "lib1"}))
            self.assertEqual(len(callback_data), 1)

        # 测试库过滤（不匹配）
        callback_data.clear()
        with patch('sse_client.KOMGA_LIBRARY_LIST', ["lib2"]):
            test_api.on_event("SeriesAdded", json.dumps({"libraryId": "lib1"}))
            self.assertEqual(len(callback_data), 0)

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
        with patch('sse_client.time.sleep') as sleep_mock:
            with patch.object(client, '_connect') as connect_mock:
                client.running = True
                client._connect()

                # 验证重试次数
                self.assertLessEqual(connect_mock.call_count, 2)
                # 验证延迟调用
                self.assertTrue(sleep_mock.called)


class TestErrorHandling(unittest.TestCase):
    """错误处理测试"""

    def setUp(self):
        # 模拟配置, 与config.template.py内容一致
        self.base_url = KOMGA_BASE_URL
        self.username = KOMGA_EMAIL
        self.password = KOMGA_EMAIL_PASSWORD
        self.client = KomgaSseClient(
            self.base_url, self.username, self.password)

    def test_invalid_json_handling(self):
        """测试无效JSON数据处理"""
        # 创建客户端
        client = self.client

        # 模拟无效JSON数据
        invalid_data = '{"invalid": true'
        with patch.object(client, 'on_error') as error_mock:
            client._dispatch_event("SeriesAdded", invalid_data)
            self.assertTrue(error_mock.called)

    def test_network_errors(self):
        """测试网络错误处理"""
        # 创建客户端
        client = self.client

        # 模拟网络错误
        self.response_mock.iter_content.side_effect = Exception(
            "Network error")

        with patch.object(client, 'on_error') as error_mock:
            client._process_stream(self.response_mock)
            self.assertTrue(error_mock.called)
