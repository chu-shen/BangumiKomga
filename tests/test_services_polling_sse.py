# -*- coding: utf-8 -*-
"""services/polling_service.py 和 services/sse_service.py 全覆盖测试"""

import unittest, threading
from unittest.mock import patch, MagicMock

import tools.log as log_mod; log_mod.logger = MagicMock()
import services.polling_service as ps_mod; ps_mod.logger = MagicMock()
import services.sse_service as ss_mod; ss_mod.logger = MagicMock()


class TestPollManager(unittest.TestCase):
    def setUp(self):
        self.stop = threading.Event()

    def test_init_defaults(self):
        from services.polling_service import PollManager
        with patch.object(PollManager, '_run'):  # 防真实执行
            pm = PollManager(self.stop, poll_interval=60, full_refresh_interval=10)
            self.assertEqual(pm._poll_interval, 60)
            self.assertEqual(pm._full_refresh_interval, 10)

    def test_start_stop(self):
        from services.polling_service import PollManager
        pm = PollManager(self.stop, poll_interval=0.05, full_refresh_interval=1)
        with patch.object(pm, '_safe_refresh'):
            pm.start()
            self.assertTrue(pm._thread.is_alive())
            pm.stop()
            self.assertTrue(self.stop.is_set())

    def test_start_idempotent(self):
        from services.polling_service import PollManager
        pm = PollManager(self.stop, poll_interval=0.05, full_refresh_interval=1)
        with patch.object(pm, '_safe_refresh'):
            pm.start(); t1 = pm._thread
            pm.start(); self.assertIs(pm._thread, t1)
            pm.stop()

    def test_safe_refresh_locking(self):
        from services.polling_service import PollManager
        pm = PollManager(self.stop)
        self.assertTrue(pm._refresh_lock.acquire(blocking=False))
        pm._refresh_lock.release()

    def test_safe_refresh_skips_when_locked(self):
        from services.polling_service import PollManager
        pm = PollManager(self.stop)
        pm._refresh_lock.acquire()
        pm._safe_refresh(lambda: None)  # 不应崩溃，应 skip
        pm._refresh_lock.release()

    def test_run_full_refresh(self):
        from services.polling_service import PollManager
        pm = PollManager(self.stop, poll_interval=0.05, full_refresh_interval=0)
        called = []
        with patch.object(pm, '_safe_refresh') as mock_sr:
            def side_effect(func):
                called.append(func.__name__)
                self.stop.set()  # 立即退出
            mock_sr.side_effect = side_effect
            pm._run()
        self.assertGreaterEqual(len(called), 1)

    def test_run_exception_handled(self):
        from services.polling_service import PollManager
        pm = PollManager(self.stop, poll_interval=0.01, full_refresh_interval=100)
        with patch.object(pm, '_safe_refresh', side_effect=RuntimeError("boom")):
            # 设 stop after a short delay
            def set_stop():
                import time; time.sleep(0.1); self.stop.set()
            threading.Thread(target=set_stop, daemon=True).start()
            pm._run()  # 不应崩溃


class TestSseManager(unittest.TestCase):
    def setUp(self):
        self.stop = threading.Event()
        self.lp = patch('api.komga_sse_api.logger').start()
        patch('api.komga_sse_api.atexit.register').start()
        patch('api.komga_sse_api.ThreadPoolExecutor').start().return_value = MagicMock()

    def tearDown(self):
        patch.stopall()

    def test_start_stop(self):
        from services.sse_service import SseManager
        with patch('api.komga_sse_api.KomgaSseClient'):
            mgr = SseManager(self.stop)
            mgr.start()
            self.assertTrue(mgr._thread.is_alive())
            mgr.stop()
            self.assertTrue(self.stop.is_set())

    def test_start_idempotent(self):
        from services.sse_service import SseManager
        with patch('api.komga_sse_api.KomgaSseClient'):
            mgr = SseManager(self.stop)
            mgr.start(); t1 = mgr._thread
            mgr.start(); self.assertIs(mgr._thread, t1)
            mgr.stop()

    def test_sse_service_handler_cbl_check(self):
        """_series_update_handler: SeriesChanged 无 CBL → 跳过"""
        from services.sse_service import _series_update_handler
        with patch('services.sse_service.get_series_metadata') as mock_get:
            mock_get.return_value = [{"metadata": {"links": []}}]
            with patch('services.sse_service.refresh_metadata') as mock_refresh:
                _series_update_handler({
                    "event_type": "SeriesChanged",
                    "event_data": {"seriesId": "s1", "libraryId": "L1"}
                })
                mock_refresh.assert_not_called()

    def test_sse_service_handler_non_cbl_skipped(self):
        """无 CBL 链接 → refresh_metadata 不调用"""
        from services.sse_service import _series_update_handler
        with patch('services.sse_service.get_series_metadata') as mock_get:
            mock_get.return_value = [{"metadata": {"links": [{"label": "Other", "url": "x"}]}}]
            with patch('services.sse_service.refresh_metadata') as mock_refresh:
                _series_update_handler({
                    "event_type": "SeriesChanged",
                    "event_data": {"seriesId": "s1", "libraryId": "L1"}
                })
                mock_refresh.assert_not_called()

    def test_sse_service_handler_surveilled_lib_skip(self):
        """不在监控范围的 library → 跳过"""
        from services.sse_service import _series_update_handler, _is_surveilled_library
        with patch('services.sse_service.KOMGA_LIBRARY_LIST', [{"LIBRARY": "L1"}]):
            self.assertTrue(_is_surveilled_library("L2"))  # L2 不在监控范围
            self.assertFalse(_is_surveilled_library("L1"))

    def test_is_surveilled_empty_list(self):
        """空 library list → 全部不过滤"""
        from services.sse_service import _is_surveilled_library
        with patch('services.sse_service.KOMGA_LIBRARY_LIST', []):
            self.assertFalse(_is_surveilled_library("anything"))
