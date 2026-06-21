# -*- coding: utf-8 -*-
"""针对 service_runner 生命周期管理的单元测试：
   poll/sse 模式的 stop_event 传递和清理流程"""

import unittest
import threading
from unittest.mock import patch, MagicMock, call

# 绕过模块级 RotatingFileHandler 创建
import tools.log as log_mod
log_mod.logger = MagicMock()

# 需要先 mock 依赖，再导入被测模块
import services.service_runner as _srv_mod
_srv_mod.logger = MagicMock()


class TestServiceRunnerLifecycle(unittest.TestCase):
    """测试 service_runner 中各模式的启停流程"""

    def setUp(self):
        self.mod = _srv_mod

    # ── _run_once_mode ─────────────────────────────────────────────

    def test_once_mode_no_archive(self):
        """once 模式：未启用 Archive 应直接跳过"""
        with patch.object(self.mod, 'periodical_archive_check_service', return_value=None):
            self.mod._run_once_mode()
            # 不应崩溃，直接执行完毕

    def test_once_mode_with_archive_completes(self):
        """once 模式：Archive 线程正常完成"""
        archive_thread = threading.Thread(target=lambda: None)
        archive_thread.start()
        archive_thread.join()  # 确保线程已完成

        with patch.object(self.mod, 'periodical_archive_check_service',
                          return_value=archive_thread):
            self.mod._run_once_mode()
            self.assertFalse(archive_thread.is_alive())

    # ── _run_poll_mode 启停 ────────────────────────────────────────

    def test_poll_mode_stop_event_passed_to_archive(self):
        """poll 模式：验证 stop_event 传给了 archive checker"""
        stop_events_received = []

        def fake_archive(stop_event=None):
            stop_events_received.append(stop_event)
            t = threading.Thread(target=lambda: None)
            t.start()
            return t

        with patch.object(self.mod, 'periodical_archive_check_service',
                          side_effect=fake_archive):
            with patch.object(self.mod, 'PollManager') as MockPoll:
                mock_poll = MagicMock()
                MockPoll.return_value = mock_poll
                with patch.object(self.mod, '_setup_stop_signals') as mock_sig:

                    def set_stop_on_signal(stop_event):
                        stop_event.set()
                    mock_sig.side_effect = set_stop_on_signal

                    self.mod._run_poll_mode()

        self.assertEqual(len(stop_events_received), 1)
        self.assertIsInstance(stop_events_received[0], threading.Event)
        mock_poll.start.assert_called_once()
        mock_poll.stop.assert_called_once()

    def test_poll_mode_archive_join_timeout(self):
        """poll 模式：archive 线程 join 超时为 60 秒且有存活检查"""
        mock_archive_thread = MagicMock()
        mock_archive_thread.is_alive.return_value = False

        def fake_archive(stop_event=None):
            return mock_archive_thread

        with patch.object(self.mod, 'periodical_archive_check_service',
                          side_effect=fake_archive):
            with patch.object(self.mod, 'PollManager') as MockPoll:
                MockPoll.return_value = MagicMock()
                with patch.object(self.mod, '_setup_stop_signals') as mock_sig:
                    mock_sig.side_effect = lambda e: e.set()

                    self.mod._run_poll_mode()

        mock_archive_thread.join.assert_called_once_with(timeout=60)
        mock_archive_thread.is_alive.assert_called()

    def test_poll_mode_archive_stuck_warning(self):
        """poll 模式：archive 线程超时未退出应有 warning"""
        mock_archive_thread = MagicMock()
        mock_archive_thread.is_alive.return_value = True  # 模拟卡住

        def fake_archive(stop_event=None):
            return mock_archive_thread

        with patch.object(self.mod, 'periodical_archive_check_service',
                          side_effect=fake_archive):
            with patch.object(self.mod, 'PollManager') as MockPoll:
                MockPoll.return_value = MagicMock()
                with patch.object(self.mod, '_setup_stop_signals') as mock_sig:
                    mock_sig.side_effect = lambda e: e.set()

                    self.mod._run_poll_mode()

        self.mod.logger.warning.assert_called()

    # ── _run_sse_mode 启停 ─────────────────────────────────────────

    def test_sse_mode_stop_event_passed_to_archive(self):
        """sse 模式：验证 stop_event 传给了 archive checker"""
        stop_events_received = []

        def fake_archive(stop_event=None):
            stop_events_received.append(stop_event)
            t = threading.Thread(target=lambda: None)
            t.start()
            return t

        with patch.object(self.mod, 'periodical_archive_check_service',
                          side_effect=fake_archive):
            with patch.object(self.mod, 'SseManager') as MockSse:
                mock_sse = MagicMock()
                MockSse.return_value = mock_sse
                with patch.object(self.mod, '_setup_stop_signals') as mock_sig:
                    mock_sig.side_effect = lambda e: e.set()

                    self.mod._run_sse_mode()

        self.assertEqual(len(stop_events_received), 1)
        self.assertIsInstance(stop_events_received[0], threading.Event)
        mock_sse.start.assert_called_once()
        mock_sse.stop.assert_called_once()

    def test_sse_mode_archive_join_timeout(self):
        """sse 模式：archive 线程 join 超时为 60 秒"""
        mock_archive_thread = MagicMock()
        mock_archive_thread.is_alive.return_value = False

        def fake_archive(stop_event=None):
            return mock_archive_thread

        with patch.object(self.mod, 'periodical_archive_check_service',
                          side_effect=fake_archive):
            with patch.object(self.mod, 'SseManager') as MockSse:
                MockSse.return_value = MagicMock()
                with patch.object(self.mod, '_setup_stop_signals') as mock_sig:
                    mock_sig.side_effect = lambda e: e.set()

                    self.mod._run_sse_mode()

        mock_archive_thread.join.assert_called_once_with(timeout=60)


class TestSetupStopSignals(unittest.TestCase):
    """测试信号处理器注册"""

    def setUp(self):
        self.mod = _srv_mod

    def test_signal_handler_sets_stop_event(self):
        """信号处理器应 set stop_event"""
        import signal

        stop_event = threading.Event()

        with patch('signal.signal') as mock_signal:
            self.mod._setup_stop_signals(stop_event)

        self.assertEqual(mock_signal.call_count, 2)
        self.assertEqual(mock_signal.call_args_list[0], call(signal.SIGINT, unittest.mock.ANY))
        self.assertEqual(mock_signal.call_args_list[1], call(signal.SIGTERM, unittest.mock.ANY))
