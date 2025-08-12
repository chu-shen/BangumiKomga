import unittest
from unittest.mock import MagicMock, patch
from api.komga_sse_api import KomgaSseClient, KomgaSseApi, RefreshEventType


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

    # 应特别注意以:
    # from config.config import KOMGA_BASE_URL, KOMGA_EMAIL, KOMGA_EMAIL_PASSWORD, KOMGA_LIBRARY_LIST
    # 方式导入的变量将作为本地变量绑定到当前模块的命名空间, 不能再使用:
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
            api.on_event("SeriesAdded", {"libraryId": "lib1"})
            self.assertEqual(len(callback_data), 1)

    def test_library_filtering_with_matching_id(self):
        """测试SSE API - 匹配KOMGA_LIBRARY_LIST时的事件分发逻辑"""
        with patch('api.komga_sse_api.KOMGA_LIBRARY_LIST', new=['lib1']):
            api = self.api
            callback_data = []

            def test_callback(data):
                callback_data.append(data)

            api.register_series_update_callback(test_callback)
            api.on_event("SeriesAdded", {"libraryId": "lib1"})
            self.assertEqual(len(callback_data), 1)

    def test_library_filtering_with_non_matching_id(self):
        """测试SSE API - 不匹配KOMGA_LIBRARY_LIST时的事件分发逻辑"""
        with patch('config.config.KOMGA_LIBRARY_LIST', new=['lib2']):
            api = self.api
            callback_data = []

            def test_callback(data):
                callback_data.append(data)

            api.register_series_update_callback(test_callback)
            api.on_event("SeriesAdded", {"libraryId": "lib1"})
            self.assertEqual(len(callback_data), 0)


# @unittest.skip("临时跳过测试")
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

        self.test_events = []

        # 模拟真实字节流传输
        self.test_event_bytes = [event.encode(
            'utf-8') for event in self.test_events]
        self.response_mock.iter_lines.side_effect = lambda chunk_size, decode_unicode: iter(
            self.test_event_bytes)

        # 创建不会发起真实请求的测试客户端
        self.client = KomgaSseClient(
            self.base_url, self.username, self.password)

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
