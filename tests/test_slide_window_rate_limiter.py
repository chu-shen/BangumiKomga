import unittest
from unittest.mock import MagicMock, patch
from tools.slide_window_rate_limiter import SlideWindowCounter, slide_window_rate_limiter


# @unittest.skip("临时跳过测试")
class TestSlideWindowCounter(unittest.TestCase):
    @patch('time.time')
    def test_basic_flow(self, mock_time):
        """测试滑动窗口限流器 - 滑动窗口计数器基本行为"""
        # 设置初始时间
        fixed_time = 1000.0
        mock_time.return_value = fixed_time

        limiter = SlideWindowCounter(max_requests=3, window_seconds=60)

        # 第一次请求应该被允许
        self.assertTrue(limiter.is_allowed())
        self.assertEqual(len(limiter.requests), 1)
        self.assertEqual(limiter.remaining_requests(), 2)

        # 模拟3次请求都在窗口内
        fixed_time += 10
        mock_time.return_value = fixed_time
        self.assertTrue(limiter.is_allowed())
        self.assertTrue(limiter.is_allowed())
        self.assertEqual(len(limiter.requests), 3)

        # 第四次请求应该被拒绝
        fixed_time += 5
        mock_time.return_value = fixed_time
        self.assertFalse(limiter.is_allowed())

        # 模拟时间超过窗口
        fixed_time += 61
        mock_time.return_value = fixed_time
        self.assertTrue(limiter.is_allowed())
        # 只保留最新请求
        self.assertEqual(len(limiter.requests), 1)

    def test_invalid_parameters(self):
        """测试滑动窗口限流器 - 无效参数输入"""
        # 测试负数参数处理（需要补充到原始代码中）
        with self.assertRaises(ValueError):
            SlideWindowCounter(-1, 60)
        with self.assertRaises(ValueError):
            SlideWindowCounter(3, -60)


class TestRateLimiterDecorator(unittest.TestCase):
    @patch('time.time')
    @patch('time.sleep')
    def test_decorator_behavior(self, mock_sleep, mock_time):
        """测试滑动窗口限流器 - 装饰器基本流程"""
        mock_time.return_value = 1000.0

        @slide_window_rate_limiter(max_requests=2, window_seconds=60, max_retries=2)
        def dummy_func():
            return "success"

         # 第一次调用成功
        self.assertEqual(dummy_func(), "success")

        # 第二次调用成功
        mock_time.return_value = 1010.0
        self.assertEqual(dummy_func(), "success")

        # 第三次调用失败（达到限制）
        mock_time.return_value = 1015.0
        with patch('tools.slide_window_rate_limiter.logger') as mock_logger:
            self.assertEqual(dummy_func(), None)  # 因为被限流且重试失败

            # 每次重试都会记录日志 3 次 以及 1 次检查是否允许请求
            self.assertEqual(mock_logger.debug.call_count, 4)

            # 验证最后一次调用是否匹配预期
            mock_logger.debug.assert_called_with("达到最大重试次数(2)")

        # 验证 sleep 被调用次数
        self.assertEqual(mock_sleep.call_count, 2)  # 两次重试
