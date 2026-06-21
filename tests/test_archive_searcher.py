# -*- coding: utf-8 -*-
"""local_archive_searcher 全覆盖测试"""

import unittest, os, tempfile, json
from unittest.mock import patch, MagicMock

import tools.log as log_mod; log_mod.logger = MagicMock()


class TestParseInfobox(unittest.TestCase):
    def test_simple(self):
        from bangumi_archive.local_archive_searcher import parse_infobox
        r = parse_infobox("|中文名=测试\n|别名=[[A]][[B]]")
        self.assertTrue(any(i["key"]=="中文名" for i in r))

    def test_multiline_value(self):
        from bangumi_archive.local_archive_searcher import parse_infobox
        r = parse_infobox("|连载杂志=周刊\nMagazine")
        self.assertTrue(any(i["key"]=="连载杂志" for i in r))

    def test_empty(self):
        from bangumi_archive.local_archive_searcher import parse_infobox
        self.assertEqual(parse_infobox(""), [])

    def test_brackets_skipped(self):
        from bangumi_archive.local_archive_searcher import parse_infobox
        r = parse_infobox("{{Infobox\n|key=val\n}}")
        self.assertEqual(len(r), 1)

    def test_no_equal_sign(self):
        from bangumi_archive.local_archive_searcher import parse_infobox
        self.assertEqual(parse_infobox("|nokey"), [])

    def test_alias_entries(self):
        from bangumi_archive.local_archive_searcher import parse_infobox
        r = parse_infobox("|别名=[[A]][[B]]")
        alias = next((i for i in r if i["key"]=="别名"), None)
        self.assertIsNotNone(alias)
        self.assertIsInstance(alias["value"], list)

    def test_link_entries(self):
        from bangumi_archive.local_archive_searcher import parse_infobox
        r = parse_infobox("|链接=[k1|v1][k2|v2]")
        link = next((i for i in r if i["key"]=="链接"), None)
        self.assertIsNotNone(link)
        self.assertIsInstance(link["value"], list)


class TestProcessValue(unittest.TestCase):
    def test_plain(self):
        from bangumi_archive.local_archive_searcher import _process_value
        self.assertEqual(_process_value("出版社","集英社"),"集英社")
    def test_alias(self):
        from bangumi_archive.local_archive_searcher import _process_value
        self.assertEqual(len(_process_value("别名","[A][B]")), 2)
    def test_link(self):
        from bangumi_archive.local_archive_searcher import _process_value
        r = _process_value("链接","[k1|v1]")
        self.assertEqual(len(r), 1); self.assertEqual(r[0]["k"],"k1")


class _BatchBase:
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "test.jsonlines")
    def tearDown(self):
        self.tmp.cleanup()
    def _write(self, items):
        with open(self.path,"w",encoding="utf-8") as f:
            for it in items: f.write(json.dumps(it,ensure_ascii=False)+"\n")


class TestSearchLineBatch(_BatchBase, unittest.TestCase):
    def test_hit(self):
        from bangumi_archive.local_archive_searcher import _search_line_batch_optimized
        self._write([{"id":1,"subject_id":100},{"id":2,"subject_id":200}])
        r = _search_line_batch_optimized(self.path, 100, "subject_id")
        self.assertIsNotNone(r); self.assertEqual(r["id"],1)

    def test_miss(self):
        from bangumi_archive.local_archive_searcher import _search_line_batch_optimized
        self._write([{"id":1,"subject_id":100}])
        self.assertIsNone(_search_line_batch_optimized(self.path, 999, "subject_id"))

    def test_file_not_found(self):
        from bangumi_archive.local_archive_searcher import _search_line_batch_optimized
        self.assertIsNone(_search_line_batch_optimized("/no/file", 100, "subject_id"))

    def test_invalid_json_skipped(self):
        from bangumi_archive.local_archive_searcher import _search_line_batch_optimized
        self._write([{"id":1,"subject_id":200}])
        with open(self.path,"a") as f: f.write("bad json\n")
        r = _search_line_batch_optimized(self.path, 200, "subject_id")
        self.assertIsNotNone(r)


class TestSearchListBatch(_BatchBase, unittest.TestCase):
    def test_multi_hit(self):
        from bangumi_archive.local_archive_searcher import _search_list_batch_optimized
        self._write([{"id":1,"subject_id":100},{"id":2,"subject_id":100}])
        self.assertEqual(len(_search_list_batch_optimized(self.path,100,"subject_id")), 2)

    def test_no_hit(self):
        from bangumi_archive.local_archive_searcher import _search_list_batch_optimized
        self._write([{"id":1,"subject_id":100}])
        self.assertEqual(_search_list_batch_optimized(self.path,999,"subject_id"), [])

    def test_file_not_found(self):
        from bangumi_archive.local_archive_searcher import _search_list_batch_optimized
        self.assertEqual(_search_list_batch_optimized("/no/file",100,"subject_id"), [])


class TestSearchAllDataBatch(_BatchBase, unittest.TestCase):
    def test_filters_type_1(self):
        from bangumi_archive.local_archive_searcher import _search_all_data_batch_optimized
        self._write([{"id":1,"type":1,"name":"SAO"},{"id":2,"type":2,"name":"SAO-EP"}])
        r = _search_all_data_batch_optimized(self.path,"SAO")
        self.assertEqual(len(r),1); self.assertEqual(r[0]["id"],1)

    def test_no_match(self):
        from bangumi_archive.local_archive_searcher import _search_all_data_batch_optimized
        self._write([{"id":1,"type":1}])
        self.assertEqual(_search_all_data_batch_optimized(self.path,"Naruto"), [])

    def test_file_not_found(self):
        from bangumi_archive.local_archive_searcher import _search_all_data_batch_optimized
        self.assertEqual(_search_all_data_batch_optimized("/no/file","X"), [])


class TestIndexModeWrappers(unittest.TestCase):
    def test_search_line_index_hit(self):
        from bangumi_archive.local_archive_searcher import _search_line_with_index
        with patch('bangumi_archive.local_archive_searcher.IndexedDataReader') as m:
            m().get_data_by_query.return_value = [{"id":1}]
            self.assertEqual(_search_line_with_index("f",100,"s")["id"], 1)

    def test_search_line_index_miss(self):
        from bangumi_archive.local_archive_searcher import _search_line_with_index
        with patch('bangumi_archive.local_archive_searcher.IndexedDataReader') as m:
            m().get_data_by_query.return_value = []
            self.assertIsNone(_search_line_with_index("f",999,"s"))

    def test_search_line_index_exception(self):
        from bangumi_archive.local_archive_searcher import _search_line_with_index
        with patch('bangumi_archive.local_archive_searcher.IndexedDataReader') as m:
            m().get_data_by_query.side_effect = FileNotFoundError("x")
            self.assertIsNone(_search_line_with_index("f",100,"s"))

    def test_search_list_index(self):
        from bangumi_archive.local_archive_searcher import _search_list_with_index
        with patch('bangumi_archive.local_archive_searcher.IndexedDataReader') as m:
            m().get_data_by_query.return_value = [{"a":1},{"a":2}]
            self.assertEqual(len(_search_list_with_index("f",100,"s")), 2)

    def test_search_list_index_empty(self):
        from bangumi_archive.local_archive_searcher import _search_list_with_index
        with patch('bangumi_archive.local_archive_searcher.IndexedDataReader') as m:
            m().get_data_by_query.return_value = []
            self.assertEqual(_search_list_with_index("f",999,"s"), [])

    def test_search_all_data_index(self):
        from bangumi_archive.local_archive_searcher import _search_all_data_with_index
        with patch('bangumi_archive.local_archive_searcher.IndexedDataReader') as m:
            m().get_data_by_query.return_value = [{"type":1,"name":"SAO"}]
            self.assertEqual(len(_search_all_data_with_index("f","SAO")), 1)

    def test_search_all_data_index_no_type1(self):
        from bangumi_archive.local_archive_searcher import _search_all_data_with_index
        with patch('bangumi_archive.local_archive_searcher.IndexedDataReader') as m:
            m().get_data_by_query.return_value = [{"type":2}]
            self.assertEqual(_search_all_data_with_index("f","X"), [])


class TestSearchLine(unittest.TestCase):
    def test_index_hit(self):
        from bangumi_archive.local_archive_searcher import search_line
        with patch('bangumi_archive.local_archive_searcher._search_line_with_index',return_value={"id":1}) as m:
            self.assertEqual(search_line("f",100,"s")["id"],1); m.assert_called_once()

    def test_index_miss_fallback(self):
        from bangumi_archive.local_archive_searcher import search_line
        with patch('bangumi_archive.local_archive_searcher._search_line_with_index',return_value=None):
            with patch('bangumi_archive.local_archive_searcher._search_line_batch_optimized',return_value={"id":2}) as m:
                self.assertEqual(search_line("f",100,"s")["id"],2); m.assert_called_once()

    def test_index_exception_fallback(self):
        from bangumi_archive.local_archive_searcher import search_line
        with patch('bangumi_archive.local_archive_searcher._search_line_with_index',side_effect=FileNotFoundError("x")):
            with patch('bangumi_archive.local_archive_searcher._search_line_batch_optimized',return_value={"id":3}) as m:
                self.assertEqual(search_line("f",100,"s")["id"],3)

    def test_generic_exception_fallback(self):
        from bangumi_archive.local_archive_searcher import search_line
        with patch('bangumi_archive.local_archive_searcher._search_line_with_index',side_effect=RuntimeError("boom")):
            with patch('bangumi_archive.local_archive_searcher._search_line_batch_optimized',return_value={"id":4}) as m:
                self.assertEqual(search_line("f",100,"s")["id"],4)


class TestSearchList(unittest.TestCase):
    def test_index_hit(self):
        from bangumi_archive.local_archive_searcher import search_list
        with patch('bangumi_archive.local_archive_searcher._search_list_with_index',return_value=[{"id":1}]) as m:
            self.assertEqual(len(search_list("f",100,"s")), 1); m.assert_called_once()

    def test_fallback(self):
        from bangumi_archive.local_archive_searcher import search_list
        with patch('bangumi_archive.local_archive_searcher._search_list_with_index',return_value=[]):
            with patch('bangumi_archive.local_archive_searcher._search_list_batch_optimized',return_value=[{"id":2}]) as m:
                self.assertEqual(len(search_list("f",100,"s")), 1); m.assert_called_once()


class TestSearchAllData(unittest.TestCase):
    def test_index_hit(self):
        from bangumi_archive.local_archive_searcher import search_all_data
        with patch('bangumi_archive.local_archive_searcher._search_all_data_with_index',return_value=[{"id":1}]) as m:
            self.assertEqual(len(search_all_data("f","t")), 1); m.assert_called_once()

    def test_fallback(self):
        from bangumi_archive.local_archive_searcher import search_all_data
        with patch('bangumi_archive.local_archive_searcher._search_all_data_with_index',return_value=[]):
            with patch('bangumi_archive.local_archive_searcher._search_all_data_batch_optimized',return_value=[{"id":2}]) as m:
                self.assertEqual(len(search_all_data("f","t")), 1); m.assert_called_once()
