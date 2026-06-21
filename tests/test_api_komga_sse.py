# -*- coding: utf-8 -*-
"""KomgaSseClient / KomgaSseApi 全覆盖测试"""

import unittest, threading
from unittest.mock import patch, MagicMock, ANY
import requests as req_mod

import tools.log as log_mod; log_mod.logger = MagicMock()
BASE = "http://mocked"


class TestSseClientInit(unittest.TestCase):
    def setUp(self):
        self.sp = patch('requests.Session').start(); self.ms = MagicMock(headers={}); self.sp.return_value = self.ms
        self.ms.get.return_value = MagicMock(status_code=200)
        self.lp = patch('api.komga_sse_api.logger').start()
        from api.komga_sse_api import KomgaSseClient; self.cls = KomgaSseClient
    def tearDown(self): patch.stopall()

    def test_api_key_success(self):
        self.ms.reset_mock(); self.ms.headers = {}; self.ms.get.return_value = MagicMock(status_code=200)
        c = self.cls(BASE,"u","p",api_key="k"); self.assertEqual(c.session.headers["X-API-Key"],"k")

    def test_api_key_failure(self):
        self.ms.reset_mock(); self.ms.headers = {}; self.ms.get.return_value = MagicMock(status_code=403)
        with self.assertRaises(Exception):
            self.cls(BASE,"u","p",api_key="k")

    def test_api_key_network_error(self):
        self.ms.reset_mock(); self.ms.headers = {}; self.ms.get.side_effect = req_mod.ConnectionError("x")
        c = self.cls(BASE,"u","p",api_key="k"); self.assertIsNotNone(c)

    def test_basic_auth_success(self):
        r = MagicMock(status_code=200); self.ms.get.return_value = r
        c = self.cls(BASE,"u","p"); self.assertIn("Authorization", c.session.headers)

    def test_basic_auth_failure(self):
        self.ms.get.return_value = MagicMock(status_code=403)
        self.cls(BASE,"u","p")  # 不崩溃

    def test_basic_auth_conn_error(self):
        self.ms.get.side_effect = req_mod.ConnectionError("x")
        self.cls(BASE,"u","p")


class TestSseClientStartStop(unittest.TestCase):
    def setUp(self):
        self.sp=patch('requests.Session').start(); self.ms=MagicMock(headers={}); self.sp.return_value=self.ms
        self.ms.get.return_value=MagicMock(status_code=200)
        self.lp=patch('api.komga_sse_api.logger').start()
        from api.komga_sse_api import KomgaSseClient; self.c=KomgaSseClient(BASE,"u","p")
    def tearDown(self): patch.stopall()

    def test_start_stop(self):
        self.c.start(); self.assertIsNotNone(self.c.thread)
        self.c.stop(); self.assertTrue(self.c._stop_event.is_set())

    def test_start_idempotent(self):
        self.c.start(); t1=self.c.thread; self.c.start()
        self.assertIs(t1, self.c.thread); self.c._stop_event.set(); self.c.thread.join(timeout=2)


class TestSseStream(unittest.TestCase):
    def setUp(self):
        self.sp=patch('requests.Session').start(); self.ms=MagicMock(headers={}); self.sp.return_value=self.ms
        self.ms.get.return_value=MagicMock(status_code=200)
        self.lp=patch('api.komga_sse_api.logger').start()
        from api.komga_sse_api import KomgaSseClient; self.c=KomgaSseClient(BASE,"u","p")
    def tearDown(self): patch.stopall()

    def test_process_stream(self):
        resp=MagicMock()
        resp.iter_lines.return_value=iter(['event: SeriesAdded','data: {"seriesId":"s1"}',''])
        events=[]; self.c.on_event=lambda e,d: events.append((e,d))
        # process_stream checks stop_event on each line; we leave it unset to process the data stream
        self.c._process_stream(resp)
        self.assertEqual(len(events),1)

    def test_stop_before_processing(self):
        resp=MagicMock(); resp.iter_lines.return_value=iter(['event: x','data: y'])
        calls=[]; self.c.on_event=lambda e,d: calls.append(1)
        self.c._stop_event.set(); self.c._process_stream(resp); self.assertEqual(len(calls),0)

    def test_parse_event_line(self):
        e,d=self.c._parse_message_line("event:BookAdded","",""); self.assertEqual(e,"BookAdded")
    def test_parse_data_line(self):
        # _parse_message_line: first data line with empty initial → stored as-is
        _,d=self.c._parse_message_line('data:{"x":1}',"",""); self.assertIn('{"x":1}',d)
    def test_parse_multidata(self):
        _,d=self.c._parse_message_line("data:line2","",'prev'); self.assertEqual(d,'prev\nline2')
    def test_parse_empty_line(self):
        dispatched=[]; self.c._dispatch_event=lambda e,d: dispatched.append((e,d))
        self.c._parse_message_line("","MyEvent","d"); self.assertEqual(len(dispatched),1)


class TestDispatchEvent(unittest.TestCase):
    def setUp(self):
        self.sp=patch('requests.Session').start(); self.ms=MagicMock(headers={}); self.sp.return_value=self.ms
        self.ms.get.return_value=MagicMock(status_code=200)
        self.lp=patch('api.komga_sse_api.logger').start()
        from api.komga_sse_api import KomgaSseClient; self.c=KomgaSseClient(BASE,"u","p")
    def tearDown(self): patch.stopall()

    def test_empty_data(self):
        events=[]; self.c.on_event=lambda e,d: events.append(1)
        self.c._dispatch_event("SeriesAdded",""); self.assertEqual(len(events),0)

    def test_list_data_error(self):
        errors=[]; self.c.on_error=lambda e: errors.append(e)
        self.c._dispatch_event("SeriesAdded","[1,2]"); self.assertTrue(len(errors)>0)

    def test_invalid_json(self):
        errors=[]; self.c.on_error=lambda e: errors.append(e)
        self.c._dispatch_event("SeriesAdded","{bad"); self.assertTrue(len(errors)>0)

    def test_subscribed_event(self):
        events=[]; self.c.on_event=lambda e,d: events.append(e)
        self.c._dispatch_event("SeriesAdded",'{"id":"s1"}'); self.assertEqual(len(events),1)

    def test_unsubscribed_event(self):
        msgs=[]; self.c.on_message=lambda d: msgs.append(d)
        self.c._dispatch_event("TaskQueueStatus",'{"count":0}'); self.assertEqual(msgs[0],{"count":0})


class TestSseApiCallbacks(unittest.TestCase):
    def setUp(self):
        self.sp=patch('requests.Session').start(); self.ms=MagicMock(headers={}); self.sp.return_value=self.ms
        self.ms.get.return_value=MagicMock(status_code=200)
        self.lp=patch('api.komga_sse_api.logger').start()
        patch('api.komga_sse_api.atexit.register').start()
        patch('api.komga_sse_api.ThreadPoolExecutor').start().return_value = MagicMock()
        from api.komga_sse_api import KomgaSseApi; self.api=KomgaSseApi(BASE,"u","p")
    def tearDown(self): patch.stopall()

    def test_register_unique(self):
        cb=lambda d:None; self.api.register_series_update_callback(cb)
        self.api.register_series_update_callback(cb); self.assertEqual(len(self.api.series_modified_callbacks),1)

    def test_unregister(self):
        cb1=lambda d:None; cb2=lambda d:None
        self.api.register_series_update_callback(cb1); self.api.register_series_update_callback(cb2)
        self.api.unregister_series_update_callback(cb1); self.assertEqual(len(self.api.series_modified_callbacks),1)

    def test_notify_no_series_id(self):
        self.api._notify_callbacks({"event_data":{"libraryId":"L1"}}); self.api.executor.submit.assert_not_called()

    def test_notify_submits(self):
        self.api.register_series_update_callback(lambda d:None)
        self.api._notify_callbacks({"event_type":"SeriesAdded","event_data":{"seriesId":"s1"}})
        self.api.executor.submit.assert_called_once()


class TestOnEventFiltering(unittest.TestCase):
    def setUp(self):
        self.sp=patch('requests.Session').start(); self.ms=MagicMock(headers={}); self.sp.return_value=self.ms
        self.ms.get.return_value=MagicMock(status_code=200)
        self.lp=patch('api.komga_sse_api.logger').start()
        patch('api.komga_sse_api.atexit.register').start()
        patch('api.komga_sse_api.ThreadPoolExecutor').start().return_value=MagicMock()
        from api.komga_sse_api import KomgaSseApi; self.api=KomgaSseApi(BASE,"u","p")
    def tearDown(self): patch.stopall()

    def test_empty_lib_list_passes(self):
        with patch('api.komga_sse_api.KOMGA_LIBRARY_LIST',new=[]):
            n=[]; self.api._notify_callbacks=lambda a:n.append(a)
            self.api.on_event("SeriesAdded",{"libraryId":"any","seriesId":"s1"}); self.assertEqual(len(n),1)

    def test_matching_lib(self):
        with patch('api.komga_sse_api.KOMGA_LIBRARY_LIST',new=[{"LIBRARY":"L1"}]):
            n=[]; self.api._notify_callbacks=lambda a:n.append(a)
            self.api.on_event("SeriesAdded",{"libraryId":"L1","seriesId":"s1"}); self.assertEqual(len(n),1)

    def test_nonmatching_lib(self):
        with patch('api.komga_sse_api.KOMGA_LIBRARY_LIST',new=[{"LIBRARY":"L1"}]):
            n=[]; self.api._notify_callbacks=lambda a:n.append(a)
            self.api.on_event("SeriesAdded",{"libraryId":"L2"}); self.assertEqual(len(n),0)

    def test_unsubscribed_event(self):
        n=[]; self.api._notify_callbacks=lambda a:n.append(a)
        self.api.on_event("TaskQueueStatus",{"count":0}); self.assertEqual(len(n),0)


class TestOnMessageError(unittest.TestCase):
    def setUp(self):
        self.sp=patch('requests.Session').start(); self.ms=MagicMock(headers={}); self.sp.return_value=self.ms
        self.ms.get.return_value=MagicMock(status_code=200)
        self.lp=patch('api.komga_sse_api.logger').start()
        patch('api.komga_sse_api.atexit.register').start()
        patch('api.komga_sse_api.ThreadPoolExecutor').start().return_value=MagicMock()
        from api.komga_sse_api import KomgaSseApi; self.api=KomgaSseApi(BASE,"u","p")
    def tearDown(self): patch.stopall()

    def test_on_message(self): self.api.on_message({"test":True})  # no crash
    def test_on_error(self): self.api.on_error(Exception("boom"))  # no crash


class TestSseApiInit(unittest.TestCase):
    @patch('api.komga_sse_api.atexit.register')
    @patch('api.komga_sse_api.ThreadPoolExecutor')
    @patch('api.komga_sse_api.KomgaSseClient')
    def test_init_registers_atexit_and_starts(self, mc, me, ma):
        mc.return_value = MagicMock(thread=MagicMock(is_alive=lambda:True))
        me.return_value = MagicMock()
        self.lp=patch('api.komga_sse_api.logger').start()
        from api.komga_sse_api import KomgaSseApi
        api = KomgaSseApi(BASE,"u","p")
        ma.assert_called(); self.assertIsNotNone(api.executor)
        patch.stopall()
