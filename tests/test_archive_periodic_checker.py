# -*- coding: utf-8 -*-
"""针对 periodic_archive_checker 的 stop_event 机制和 parse_interval 单元测试"""

import unittest
import threading
import time
from unittest.mock import patch, MagicMock

# 绕过模块级 RotatingFileHandler 创建 —— 必须在 import 被测模块之前 mock logger
import tools.log as log_mod
log_mod.logger = MagicMock()

from bangumi_archive.periodic_archive_checker import (
    parse_interval,
    periodical_archive_check_service as _periodical_archive_check_service,
)


class TestParseInterval(unittest.TestCase):
    """测试时间间隔解析"""

    def test_parse_interval_hours(self):
        self.assertEqual(parse_interval(hours=24), 86400)
        self.assertEqual(parse_interval(hours=1), 3600)

    def test_parse_interval_multiple_units(self):
        self.assertEqual(parse_interval(days=1, hours=1, minutes=30, seconds=45),
                         86400 + 3600 + 1800 + 45)

    def test_parse_interval_zero(self):
        self.assertEqual(parse_interval(), 0)

    def test_parse_interval_negative_raises(self):
        with self.assertRaises(ValueError):
            parse_interval(hours=-1)


class TestPeriodicalArchiveCheckService(unittest.TestCase):
    """测试定时检查服务的 stop_event 机制"""

    def setUp(self):
        # 恢复模块级变量为默认值，避免测试间互相污染
        import bangumi_archive.periodic_archive_checker as pac_mod
        self._pac_mod = pac_mod
        self._orig_use_archive = pac_mod.USE_BANGUMI_ARCHIVE
        self._orig_interval = pac_mod.ARCHIVE_UPDATE_INTERVAL

    def tearDown(self):
        self._pac_mod.USE_BANGUMI_ARCHIVE = self._orig_use_archive
        self._pac_mod.ARCHIVE_UPDATE_INTERVAL = self._orig_interval

    def test_returns_none_when_archive_disabled(self):
        """禁用 Archive 时返回 None"""
        self._pac_mod.USE_BANGUMI_ARCHIVE = False
        result = _periodical_archive_check_service()
        self.assertIsNone(result)

    def test_returns_none_when_interval_zero(self):
        """更新间隔为 0 时返回 None"""
        self._pac_mod.USE_BANGUMI_ARCHIVE = True
        self._pac_mod.ARCHIVE_UPDATE_INTERVAL = 0
        result = _periodical_archive_check_service()
        self.assertIsNone(result)

    def test_no_stop_event_creates_default(self):
        """未传入 stop_event 时应自动创建，线程能正常启动"""
        self._pac_mod.USE_BANGUMI_ARCHIVE = True
        self._pac_mod.ARCHIVE_UPDATE_INTERVAL = 24

        with patch('bangumi_archive.periodic_archive_checker.check_archive') as mock_check:
            thread = _periodical_archive_check_service()
            self.assertIsNotNone(thread)
            self.assertTrue(thread.is_alive())

            time.sleep(0.3)
            mock_check.assert_called()

    def test_stop_event_stops_thread(self):
        """传入 stop_event，set 后线程应在合理时间内退出"""
        self._pac_mod.USE_BANGUMI_ARCHIVE = True
        self._pac_mod.ARCHIVE_UPDATE_INTERVAL = 24

        with patch('bangumi_archive.periodic_archive_checker.check_archive') as mock_check:
            stop_event = threading.Event()
            thread = _periodical_archive_check_service(stop_event)
            self.assertIsNotNone(thread)
            self.assertTrue(thread.is_alive())

            time.sleep(0.3)
            mock_check.assert_called()

            stop_event.set()
            thread.join(timeout=5)
            self.assertFalse(thread.is_alive(),
                             "stop_event.set() 后线程应在 5 秒内退出")

    def test_stop_event_before_first_check(self):
        """在 check_archive 第一次调用前就 set stop_event，线程应立即退出"""
        self._pac_mod.USE_BANGUMI_ARCHIVE = True
        self._pac_mod.ARCHIVE_UPDATE_INTERVAL = 24

        with patch('bangumi_archive.periodic_archive_checker.check_archive') as mock_check:
            stop_event = threading.Event()
            stop_event.set()
            thread = _periodical_archive_check_service(stop_event)
            self.assertIsNotNone(thread)

            thread.join(timeout=5)
            self.assertFalse(thread.is_alive(),
                             "stop_event 已预设，线程应立即退出（最多 5 秒）")
            self.assertLessEqual(mock_check.call_count, 1)

    def test_exception_in_check_archive_does_not_crash_thread(self):
        """check_archive 抛出异常不应导致线程崩溃"""
        self._pac_mod.USE_BANGUMI_ARCHIVE = True
        self._pac_mod.ARCHIVE_UPDATE_INTERVAL = 24

        with patch('bangumi_archive.periodic_archive_checker.check_archive',
                   side_effect=RuntimeError("模拟异常")):
            stop_event = threading.Event()
            thread = _periodical_archive_check_service(stop_event)
            self.assertIsNotNone(thread)

            time.sleep(0.5)
            self.assertTrue(thread.is_alive(),
                            "check_archive 异常后线程应继续存活")

            stop_event.set()
            thread.join(timeout=5)
            self.assertFalse(thread.is_alive())
