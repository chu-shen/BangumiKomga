# -*- coding: utf-8 -*-
"""KomgaApi 测试：覆盖认证、系列、书籍、收藏、库、元数据类"""

import unittest
from unittest.mock import patch, MagicMock, ANY
import requests as req_mod

# 绕过 RotatingFileHandler
import tools.log as log_mod
log_mod.logger = MagicMock()

BASE = "http://localhost:25600"
API_BASE = BASE + "/api/v1"


# ═══════════════════════════════════════════════════════════════════
# 基类：创建 Mock KomgaApi
# ═══════════════════════════════════════════════════════════════════
class _Base(unittest.TestCase):
    def setUp(self):
        self.sp = patch('requests.Session').start()
        self.m_sess = MagicMock()
        self.m_sess.headers = {}
        self.sp.return_value = self.m_sess
        # Basic Auth 认证 → 204
        r = MagicMock()
        r.status_code = 204
        self.m_sess.get.return_value = r
        self.lp = patch('api.komga_api.logger').start()
        from api.komga_api import KomgaApi
        self.api = KomgaApi(BASE, "u", "p")

    def tearDown(self):
        patch.stopall()


# ═══════════════════════════════════════════════════════════════════
# 构造函数
# ═══════════════════════════════════════════════════════════════════
class TestInit(_Base):
    def test_basic_auth_success(self):
        self.assertEqual(self.api.base_url, API_BASE)
        self.m_sess.mount.assert_any_call("http://", ANY)
        self.m_sess.mount.assert_any_call("https://", ANY)

    def test_api_key_success(self):
        """api_key 模式：认证请求 /api/v2/users/me 返回 200"""
        self.m_sess.reset_mock()
        self.m_sess.headers = {}
        r = MagicMock()
        r.status_code = 200
        self.m_sess.get.return_value = r
        from api.komga_api import KomgaApi
        api = KomgaApi(BASE, "u", "p", api_key="k")
        self.assertEqual(api.r.headers["X-API-Key"], "k")

    def test_api_key_failure_exits(self):
        """api_key 模式：/api/v2/users/me 返回非 200 → exit(1)"""
        self.m_sess.reset_mock()
        self.m_sess.headers = {}
        r = MagicMock()
        r.status_code = 403
        self.m_sess.get.return_value = r
        with self.assertRaises(SystemExit):
            from api.komga_api import KomgaApi
            KomgaApi(BASE, "u", "p", api_key="k")

    def test_basic_auth_failure_exits(self):
        """Basic Auth 失败 → exit(1)"""
        self.m_sess.reset_mock()
        self.m_sess.headers = {}
        r = MagicMock()
        r.status_code = 401
        self.m_sess.get.return_value = r
        with self.assertRaises(SystemExit):
            from api.komga_api import KomgaApi
            KomgaApi(BASE, "u", "p")


# ═══════════════════════════════════════════════════════════════════
# get_latest_series
# ═══════════════════════════════════════════════════════════════════
class TestGetLatestSeries(_Base):
    def test_success_no_library(self):
        r = MagicMock()
        r.status_code = 200
        r.json.return_value = {"content": []}
        self.m_sess.get.return_value = r
        res = self.api.get_latest_series()
        self.assertEqual(res, {"content": []})

    def test_success_with_string_library(self):
        r = MagicMock()
        r.status_code = 200
        r.json.return_value = {"content": [1]}
        self.m_sess.get.return_value = r
        res = self.api.get_latest_series(library_id="L1")
        self.assertEqual(res, {"content": [1]})

    def test_success_with_list_library(self):
        r = MagicMock()
        r.json.return_value = {"content": [2]}
        self.m_sess.get.return_value = r
        res = self.api.get_latest_series(library_id=["L1", "L2"])
        self.assertEqual(res, {"content": [2]})

    def test_request_exception(self):
        self.m_sess.get.side_effect = req_mod.ConnectionError("x")
        self.assertEqual(self.api.get_latest_series(), [])


# ═══════════════════════════════════════════════════════════════════
# get_specific_series
# ═══════════════════════════════════════════════════════════════════
class TestGetSpecificSeries(_Base):
    def test_success(self):
        r = MagicMock()
        r.json.return_value = {"id": "s1"}
        self.m_sess.get.return_value = r
        self.assertEqual(self.api.get_specific_series("s1"), {"id": "s1"})

    def test_exception(self):
        self.m_sess.get.side_effect = req_mod.ConnectionError("x")
        self.assertEqual(self.api.get_specific_series("s1"), [])


# ═══════════════════════════════════════════════════════════════════
# get_all_series
# ═══════════════════════════════════════════════════════════════════
class TestGetAllSeries(_Base):
    def test_success_no_extra_payload(self):
        r = MagicMock()
        r.json.return_value = {"content": []}
        self.m_sess.post.return_value = r
        res = self.api.get_all_series()
        self.assertEqual(res, {"content": []})

    def test_success_with_payload(self):
        r = MagicMock()
        r.json.return_value = {"content": ["x"]}
        self.m_sess.post.return_value = r
        res = self.api.get_all_series(payload={"readStatus": {"operator": "is", "value": "READ"}})
        self.assertEqual(res, {"content": ["x"]})

    def test_exception(self):
        self.m_sess.post.side_effect = req_mod.ConnectionError("x")
        self.assertEqual(self.api.get_all_series(), [])


# ═══════════════════════════════════════════════════════════════════
# get_series_with_*
# ═══════════════════════════════════════════════════════════════════
class TestGetSeriesWith(_Base):
    def test_libraryid_single(self):
        r = MagicMock()
        r.json.return_value = {"content": ["x"]}
        self.m_sess.post.return_value = r
        res = self.api.get_series_with_libraryid(["L1"])
        self.assertIn("content", res)

    def test_libraryid_multiple(self):
        r = MagicMock()
        r.json.return_value = {"content": []}
        self.m_sess.post.return_value = r
        res = self.api.get_series_with_libraryid(["L1", "L2"])
        self.assertIn("content", res)

    def test_collection_single(self):
        r = MagicMock()
        r.json.return_value = {"content": []}
        self.m_sess.post.return_value = r
        res = self.api.get_series_with_collection(["C1"])
        self.assertIn("content", res)

    def test_collection_multiple(self):
        r = MagicMock()
        r.json.return_value = {"content": []}
        self.m_sess.post.return_value = r
        res = self.api.get_series_with_collection(["C1", "C2"])
        self.assertIn("content", res)

    def test_read_status(self):
        r = MagicMock()
        r.json.return_value = {"content": []}
        self.m_sess.post.return_value = r
        res = self.api.get_series_with_read_status("READ")
        self.assertIn("content", res)


# ═══════════════════════════════════════════════════════════════════
# get_series_with_readlist
# ═══════════════════════════════════════════════════════════════════
class TestGetSeriesWithReadlist(_Base):
    def test_success(self):
        r = MagicMock()
        r.json.return_value = {"seriesIds": []}
        self.m_sess.get.return_value = r
        self.assertEqual(self.api.get_series_with_readlist("rl1"), {"seriesIds": []})

    def test_exception(self):
        self.m_sess.get.side_effect = req_mod.ConnectionError("x")
        self.assertEqual(self.api.get_series_with_readlist("rl1"), [])


# ═══════════════════════════════════════════════════════════════════
# get_series_books / get_series_thumbnails / get_book_thumbnails
# ═══════════════════════════════════════════════════════════════════
class TestGetters(_Base):
    def test_series_books_success(self):
        r = MagicMock()
        r.json.return_value = {"content": []}
        self.m_sess.post.return_value = r
        self.assertEqual(self.api.get_series_books("s1"), {"content": []})

    def test_series_books_exception(self):
        self.m_sess.post.side_effect = req_mod.ConnectionError("x")
        self.assertEqual(self.api.get_series_books("s1"), [])

    def test_series_thumbnails_success(self):
        r = MagicMock()
        r.json.return_value = [{"id": "t1"}]
        self.m_sess.get.return_value = r
        self.assertEqual(self.api.get_series_thumbnails("s1"), [{"id": "t1"}])

    def test_series_thumbnails_exception(self):
        self.m_sess.get.side_effect = req_mod.ConnectionError("x")
        self.assertEqual(self.api.get_series_thumbnails("s1"), [])

    def test_book_thumbnails_success(self):
        r = MagicMock()
        r.json.return_value = [{"id": "t2"}]
        self.m_sess.get.return_value = r
        self.assertEqual(self.api.get_book_thumbnails("b1"), [{"id": "t2"}])

    def test_book_thumbnails_exception(self):
        self.m_sess.get.side_effect = req_mod.ConnectionError("x")
        self.assertEqual(self.api.get_book_thumbnails("b1"), [])


# ═══════════════════════════════════════════════════════════════════
# update_series_metadata / update_book_metadata
# ═══════════════════════════════════════════════════════════════════
class TestUpdateMetadata(_Base):
    def test_update_series_success(self):
        r = MagicMock()
        r.status_code = 204
        self.m_sess.patch.return_value = r
        self.assertTrue(self.api.update_series_metadata("s1", {"title": "T"}))

    def test_update_series_failure(self):
        r = MagicMock()
        r.status_code = 400
        self.m_sess.patch.return_value = r
        self.assertFalse(self.api.update_series_metadata("s1", {}))

    def test_update_series_exception(self):
        self.m_sess.patch.side_effect = req_mod.ConnectionError("x")
        self.assertFalse(self.api.update_series_metadata("s1", {}))

    def test_update_book_success(self):
        r = MagicMock()
        r.status_code = 204
        self.m_sess.patch.return_value = r
        self.assertTrue(self.api.update_book_metadata("b1", {"number": 1}))

    def test_update_book_failure(self):
        r = MagicMock()
        r.status_code = 400
        self.m_sess.patch.return_value = r
        self.assertFalse(self.api.update_book_metadata("b1", {}))

    def test_update_book_exception(self):
        self.m_sess.patch.side_effect = req_mod.ConnectionError("x")
        self.assertFalse(self.api.update_book_metadata("b1", {}))


# ═══════════════════════════════════════════════════════════════════
# update_series_thumbnail / update_book_thumbnail
# ═══════════════════════════════════════════════════════════════════
class TestUpdateThumbnails(_Base):
    def test_series_thumbnail_success(self):
        r = MagicMock()
        r.status_code = 200
        self.m_sess.post.return_value = r
        self.assertTrue(self.api.update_series_thumbnail("s1", {"file": b"x"}))

    def test_series_thumbnail_failure(self):
        r = MagicMock()
        r.status_code = 400
        self.m_sess.post.return_value = r
        self.assertFalse(self.api.update_series_thumbnail("s1", {}))

    def test_series_thumbnail_413(self):
        """413 Payload Too Large → 特殊错误消息"""
        from requests.exceptions import HTTPError
        resp = MagicMock()
        resp.status_code = 413
        self.m_sess.post.side_effect = HTTPError(response=resp)
        self.m_sess.post.side_effect.response = resp
        self.assertFalse(self.api.update_series_thumbnail("s1", {"file": b"big"}))

    def test_series_thumbnail_exception_no_response(self):
        self.m_sess.post.side_effect = req_mod.ConnectionError("x")
        self.assertFalse(self.api.update_series_thumbnail("s1", {}))

    def test_book_thumbnail_success(self):
        r = MagicMock()
        r.status_code = 200
        self.m_sess.post.return_value = r
        self.assertTrue(self.api.update_book_thumbnail("b1", {"file": b"x"}))

    def test_book_thumbnail_failure(self):
        r = MagicMock()
        r.status_code = 400
        self.m_sess.post.return_value = r
        self.assertFalse(self.api.update_book_thumbnail("b1", {}))

    def test_book_thumbnail_exception(self):
        self.m_sess.post.side_effect = req_mod.ConnectionError("x")
        self.assertFalse(self.api.update_book_thumbnail("b1", {}))


# ═══════════════════════════════════════════════════════════════════
# add_collection
# ═══════════════════════════════════════════════════════════════════
class TestAddCollection(_Base):
    def test_success(self):
        r = MagicMock()
        r.status_code = 200
        self.m_sess.post.return_value = r
        self.assertTrue(self.api.add_collection("C", False, ["s1"]))

    def test_failure(self):
        r = MagicMock()
        r.status_code = 400
        self.m_sess.post.return_value = r
        self.assertFalse(self.api.add_collection("C", False, []))

    def test_exception(self):
        self.m_sess.post.side_effect = req_mod.ConnectionError("x")
        self.assertFalse(self.api.add_collection("C", False, []))


# ═══════════════════════════════════════════════════════════════════
# get_collection_id_by_search_name / get_series_ids_by_collection_name
# ═══════════════════════════════════════════════════════════════════
class TestCollectionSearch(_Base):
    def test_search_found(self):
        r = MagicMock()
        r.json.return_value = {"content": [{"id": "c1", "name": "FAILED"}]}
        self.m_sess.get.return_value = r
        self.assertEqual(self.api.get_collection_id_by_search_name("FAILED"), "c1")

    def test_search_not_found(self):
        r = MagicMock()
        r.json.return_value = {"content": []}
        self.m_sess.get.return_value = r
        self.assertIsNone(self.api.get_collection_id_by_search_name("X"))

    def test_search_exception(self):
        self.m_sess.get.side_effect = req_mod.ConnectionError("x")
        self.assertIsNone(self.api.get_collection_id_by_search_name("X"))

    def test_series_ids_found(self):
        """get_series_ids_by_collection_name: 找到 collection 且有 seriesIds"""
        responses = [
            MagicMock(**{"json.return_value": {"content": [{"id": "c1"}]}}),
            MagicMock(**{"json.return_value": {"seriesIds": ["s1", "s2"]}}),
        ]
        self.m_sess.get.side_effect = responses
        self.assertEqual(self.api.get_series_ids_by_collection_name("F"), ["s1", "s2"])

    def test_series_ids_not_found_collection(self):
        """collection 不存在 → None"""
        r = MagicMock()
        r.json.return_value = {"content": []}
        self.m_sess.get.return_value = r
        self.assertIsNone(self.api.get_series_ids_by_collection_name("X"))

    def test_series_ids_empty_series_ids(self):
        """collection 存在但 seriesIds 为空 → None"""
        responses = [
            MagicMock(**{"json.return_value": {"content": [{"id": "c1"}]}}),
            MagicMock(**{"json.return_value": {"seriesIds": []}}),
        ]
        self.m_sess.get.side_effect = responses
        self.assertIsNone(self.api.get_series_ids_by_collection_name("F"))

    def test_series_ids_exception_on_search(self):
        """搜索时网络异常 → None"""
        self.m_sess.get.side_effect = req_mod.ConnectionError("x")
        self.assertIsNone(self.api.get_series_ids_by_collection_name("F"))

    def test_series_ids_exception_on_get_by_id(self):
        """找到 collection ID 但获取详情时网络异常 → None"""
        responses = [
            MagicMock(**{"json.return_value": {"content": [{"id": "c1"}]}}),
            req_mod.ConnectionError("x"),
        ]
        self.m_sess.get.side_effect = responses
        self.assertIsNone(self.api.get_series_ids_by_collection_name("F"))


# ═══════════════════════════════════════════════════════════════════
# delete_collection
# ═══════════════════════════════════════════════════════════════════
class TestDeleteCollection(_Base):
    def test_success(self):
        r = MagicMock()
        r.status_code = 204
        self.m_sess.delete.return_value = r
        self.assertTrue(self.api.delete_collection("c1"))

    def test_failure(self):
        r = MagicMock()
        r.status_code = 400
        self.m_sess.delete.return_value = r
        self.assertFalse(self.api.delete_collection("c1"))

    def test_exception(self):
        self.m_sess.delete.side_effect = req_mod.ConnectionError("x")
        self.assertFalse(self.api.delete_collection("c1"))


# ═══════════════════════════════════════════════════════════════════
# update_collection / replace_collection
# ═══════════════════════════════════════════════════════════════════
class TestUpdateReplaceCollection(_Base):
    def test_update_collection_success(self):
        r = MagicMock()
        r.status_code = 204
        self.m_sess.patch.return_value = r
        self.assertTrue(self.api.update_collection("c1", False, ["s1"]))

    def test_update_collection_failure(self):
        r = MagicMock()
        r.status_code = 400
        self.m_sess.patch.return_value = r
        self.assertFalse(self.api.update_collection("c1", True, ["s1"]))

    def test_update_collection_exception(self):
        self.m_sess.patch.side_effect = req_mod.ConnectionError("x")
        self.assertFalse(self.api.update_collection("c1", False, []))

    def test_replace_updates_when_exists(self):
        with patch.object(self.api, 'get_collection_id_by_search_name', return_value="c1"):
            with patch.object(self.api, 'update_collection', return_value=True) as mu:
                with patch.object(self.api, 'add_collection') as ma:
                    self.assertTrue(self.api.replace_collection("F", False, ["s1"]))
                    mu.assert_called_once_with("c1", False, ["s1"])
                    ma.assert_not_called()

    def test_replace_creates_when_not_exists(self):
        with patch.object(self.api, 'get_collection_id_by_search_name', return_value=None):
            with patch.object(self.api, 'add_collection', return_value=True) as ma:
                with patch.object(self.api, 'update_collection') as mu:
                    self.assertTrue(self.api.replace_collection("F", True, ["s1"]))
                    ma.assert_called_once_with("F", True, ["s1"])
                    mu.assert_not_called()

    def test_replace_update_failure(self):
        with patch.object(self.api, 'get_collection_id_by_search_name', return_value="c1"):
            with patch.object(self.api, 'update_collection', return_value=False):
                self.assertFalse(self.api.replace_collection("F", False, ["s1"]))

    def test_replace_add_failure(self):
        with patch.object(self.api, 'get_collection_id_by_search_name', return_value=None):
            with patch.object(self.api, 'add_collection', return_value=False):
                self.assertFalse(self.api.replace_collection("N", False, ["s1"]))

    def test_replace_never_calls_delete(self):
        with patch.object(self.api, 'get_collection_id_by_search_name', return_value="c1"):
            with patch.object(self.api, 'update_collection', return_value=True):
                with patch.object(self.api, 'delete_collection') as md:
                    self.api.replace_collection("F", False, ["s1"])
                    md.assert_not_called()
        with patch.object(self.api, 'get_collection_id_by_search_name', return_value=None):
            with patch.object(self.api, 'add_collection', return_value=True):
                with patch.object(self.api, 'delete_collection') as md:
                    self.api.replace_collection("F", False, ["s1"])
                    md.assert_not_called()


# ═══════════════════════════════════════════════════════════════════
# list_libraries / list_collections
# ═══════════════════════════════════════════════════════════════════
class TestListLibraries(_Base):
    def test_success_with_results(self):
        r = MagicMock()
        r.json.return_value = [{"id": "L1"}]
        self.m_sess.get.return_value = r
        self.assertEqual(self.api.list_libraries(), [{"id": "L1"}])

    def test_success_empty(self):
        r = MagicMock()
        r.json.return_value = []
        self.m_sess.get.return_value = r
        self.assertEqual(self.api.list_libraries(), [])

    def test_exception(self):
        self.m_sess.get.side_effect = req_mod.ConnectionError("x")
        self.assertEqual(self.api.list_libraries(), [])


class TestListCollections(_Base):
    def test_success_with_results(self):
        r = MagicMock()
        r.json.return_value = {"content": [{"id": "C1"}]}
        self.m_sess.get.return_value = r
        self.assertEqual(self.api.list_collections(), [{"id": "C1"}])

    def test_success_empty(self):
        r = MagicMock()
        r.json.return_value = {"content": []}
        self.m_sess.get.return_value = r
        self.assertEqual(self.api.list_collections(), [])

    def test_exception(self):
        self.m_sess.get.side_effect = req_mod.ConnectionError("x")
        self.assertEqual(self.api.list_collections(), [])


# ═══════════════════════════════════════════════════════════════════
# SeriesMetadata / BookMetadata
# ═══════════════════════════════════════════════════════════════════
class TestSeriesMetadata(unittest.TestCase):
    def test_defaults(self):
        from api.komga_api import SeriesMetadata
        m = SeriesMetadata()
        self.assertEqual(m.title, "")
        self.assertEqual(m.status, "")
        self.assertEqual(m.summary, "")
        self.assertEqual(m.publisher, "")
        self.assertEqual(m.genres, "[]")
        self.assertEqual(m.tags, "[]")
        self.assertEqual(m.alternateTitles, "[]")
        self.assertEqual(m.ageRating, 12)
        self.assertEqual(m.language, "zh-CN")
        self.assertEqual(m.links, "[]")
        self.assertEqual(m.totalBookCount, 1)
        self.assertEqual(m.titleSort, "")
        self.assertFalse(m.isvalid)


class TestBookMetadata(unittest.TestCase):
    def test_defaults(self):
        from api.komga_api import BookMetadata
        m = BookMetadata()
        self.assertEqual(m.title, "")
        self.assertEqual(m.summary, "")
        self.assertEqual(m.number, 0)
        self.assertEqual(m.isbn, "")
        self.assertEqual(m.authors, "[]")
        self.assertEqual(m.tags, "[]")
        self.assertIsNone(m.releaseDate)
        self.assertEqual(m.links, "[]")
        self.assertEqual(m.numberSort, 0)
        self.assertFalse(m.isvalid)
