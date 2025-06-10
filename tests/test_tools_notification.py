import unittest
from unittest.mock import patch, Mock
import requests
from tools.log import logger
from tools.notification import send_notification


class TestNotification(unittest.TestCase):
    def setUp(self):
        # 创建通用测试数据
        self.title = "测试标题"
        self.message = "测试内容"

        # 创建mock logger
        self.logger_info_mock = patch('tools.notification.logger.info').start()
        self.logger_error_mock = patch(
            'tools.notification.logger.error').start()
        self.logger_debug_mock = patch(
            'tools.notification.logger.debug').start()

    def tearDown(self):
        patch.stopall()

    @patch.multiple('tools.notification',
                    NOTIF_TYPE_ENABLE=['GOTIFY'],
                    NOTIF_GOTIFY_ENDPOINT='http://test.com',
                    NOTIF_GOTIFY_TOKEN='test_token')
    @patch('tools.notification.requests.post')
    def test_gotify_success(self, mock_post):
        """测试通知发送 - 成功发送Gotify通知"""
        # 配置mock响应
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        send_notification(self.title, self.message)

        # 验证调用
        mock_post.assert_called_once()
        self.logger_info_mock.assert_called_once_with("GOTIFY: 成功发送通知")

    @patch.multiple('tools.notification',
                    NOTIF_TYPE_ENABLE=['WEBHOOK'],
                    NOTIF_WEBHOOK_METHOD="POST",
                    NOTIF_WEBHOOK_ENDPOINT="http://webhook.test")
    @patch('tools.notification.requests.request')
    def test_webhook_failure(self, mock_post):
        """测试通知发送 - 发送Webhook通知失败"""
        # 配置mock响应
        mock_response = Mock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response

        send_notification(self.title, self.message)

        # 验证调用
        mock_post.assert_called_once()
        self.logger_error_mock.assert_called_once_with("WEBHOOK: 发送通知失败")

    @patch.multiple('tools.notification',
                    NOTIF_TYPE_ENABLE=["HEALTHCHECKS"],
                    NOTIF_HEALTHCHECKS_ENDPOINT="http://healthcheck.test")
    @patch('tools.notification.requests.get')
    def test_healthchecks_success(self, mock_get):
        """测试通知发送 - 通过健康检查"""
        # 配置mock响应
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        send_notification(self.title, self.message)

        # 验证调用
        mock_get.assert_called_once()
        self.logger_debug_mock.assert_called_once_with("HEALTHCHECKS 通过")

    @patch.multiple('tools.notification',
                    NOTIF_TYPE_ENABLE=["HEALTHCHECKS"],
                    NOTIF_HEALTHCHECKS_ENDPOINT="http://healthcheck.test")
    @patch('tools.notification.requests.get')
    def test_healthchecks_failure(self, mock_get):
        """测试通知发送 - 健康检查失败"""
        # 模拟请求异常
        mock_get.side_effect = requests.exceptions.RequestException("连接失败")

        send_notification(self.title, self.message)

        # 验证调用
        mock_get.assert_called_once()
        self.logger_error_mock.assert_called_once_with(
            "HEALTHCHECKS: Ping 失败。错误: 连接失败")

    @patch.multiple('tools.notification',
                    NOTIF_TYPE_ENABLE=["UNKNOWN"])
    def test_unknown_notification_type(self):
        """测试通知发送 - 错误的通知类型"""

        send_notification(self.title, self.message)

        # 验证没有进行任何网络请求
        self.logger_info_mock.assert_not_called()
        self.logger_error_mock.assert_not_called()
