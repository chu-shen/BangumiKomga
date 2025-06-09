import unittest
from unittest.mock import patch, MagicMock, mock_open
import json
from bangumi_archive.local_archive_searcher import (  # 替换为实际模块名
    search_line,
    search_list,
    search_all_data,
    parse_infobox,
    _process_value
)


class TestSearchFunctions(unittest.TestCase):
    def setUp(self):
        # 创建通用测试数据
        self.test_file = "test_archive.jsonl"
        self.test_data = [
            {"id": 1, "name": "Test1", "type": 1},
            {"id": 2, "name": "Test2", "type": 1}
        ]

    @patch('bangumi_archive.indexed_jsonlines_read.IndexedDataReader')  # 替换为实际模块名
    def test_search_line_with_index_hit(self, mock_indexed_reader):
        """测试带索引的单行搜索命中情况"""
        # 模拟IndexedDataReader返回数据
        mock_instance = mock_indexed_reader.return_value
        mock_instance.__iter__.return_value = [self.test_data[0]]

        result = search_line(self.test_file, 1, "id")
        self.assertEqual(result, self.test_data[0])

    @patch('bangumi_archive.local_archive_searcher._search_line_with_index')
    @patch('bangumi_archive.local_archive_searcher._search_line_batch_optimized')
    def test_search_line_index_miss_fallback(self, mock_batch, mock_index):
        """测试索引未命中时回退到批量模式"""
        # 设置索引模式返回None
        mock_index.return_value = None
        # 设置批量模式返回数据
        mock_batch.return_value = self.test_data[0]

        result = search_line(self.test_file, 1, "id")
        self.assertEqual(result, self.test_data[0])
        mock_batch.assert_called_once()

    @patch('bangumi_archive.local_archive_searcher.open', new_callable=mock_open, read_data=json.dumps({"id": 1, "name": "Test"}))
    def test_search_line_batch_hit(self, mock_file):
        """测试批量模式单行命中"""
        from bangumi_archive.local_archive_searcher import _search_line_batch_optimized
        result = _search_line_batch_optimized(self.test_file, 1, "id")
        self.assertEqual(result["id"], 1)

    def test_search_list_basic(self):
        """测试搜索列表基础功能"""
        with patch('bangumi_archive.local_archive_searcher._search_list_with_index') as mock_index:
            mock_index.return_value = self.test_data
            result = search_list(self.test_file, 1, "id")
            self.assertEqual(len(result), 2)

    @patch('bangumi_archive.local_archive_searcher._search_all_data_with_index')
    @patch('bangumi_archive.local_archive_searcher._search_all_data_batch_optimized')
    def test_search_all_data_index_hit(self, mock_batch, mock_index):
        """测试全量数据搜索索引命中"""
        mock_index.return_value = self.test_data
        result = search_all_data(self.test_file, "test")
        self.assertEqual(len(result), 2)
        mock_index.assert_called_once()

    def test_parse_infobox_basic(self):
        """测试infobox基础解析"""
        test_str = "|key1=value1\n|key2=value2"
        result = parse_infobox(test_str)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["key"], "key1")

    def test_process_value_alias(self):
        """测试别名字段处理"""
        result = _process_value("别名", "[alias1][ alias2 ]")
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["v"], "alias1")
