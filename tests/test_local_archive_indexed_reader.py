import json
import os
import pickle
import tempfile
import unittest
from unittest.mock import patch, MagicMock, mock_open

from bangumi_archive.local_archive_indexed_reader import IndexedDataReader


class TestIndexedDataReader(unittest.TestCase):
    def setUp(self):
        """准备测试数据及文件"""
        self.sample_subject_data = [
            {"id": 328150, "type": 1, "name": "ニューノーマル", "name_cn": "新常态",
                "infobox": "{{Infobox animanga/Manga\r\n|中文名= 新常态\r\n|别名={\r\n[你和我的嘴唇]\r\n[未来的恋爱必须戴口罩]\r\n[New Normal]\r\n}\r\n|出版社= ファンギルド\r\n|价格= \r\n|其他出版社= \r\n|连载杂志= \r\n|发售日= 2021-07-19\r\n|册数= \r\n|页数= \r\n|话数= \r\n|ISBN= \r\n|其他= \r\n|作者= 相原瑛人\r\n|开始= 2020-12-18\r\n}}", "platform": 1001},
            {"id": 241596, "type": 2, "name": "Mickey's Trailer", "name_cn": "米奇的房车",
                "infobox": "{{Infobox animanga/Anime\r\n|中文名= 米奇的房车\r\n|别名={\r\n}\r\n|上映年度= 1938-05-06\r\n|片长= 7分钟\r\n}}", "platform": 0},
            {"id": 497, "type": 1, "name": "ちょびっツ", "name_cn": "人形电脑天使心",
                "infobox": "{{Infobox animanga/Manga\r\n|中文名= 人形电脑天使心\r\n|别名={\r\n[en|Chobits]\r\n}\r\n|出版社= 講談社\r\n}}", "platform": 1001},
            {"id": 252236, "type": 1, "name": "GREASEBERRIES 2", "name_cn": "",
                "infobox": "{{Infobox animanga/Manga\r\n|中文名= \r\n|别名={\r\n}\r\n|作者= 士郎正宗\r\n}}", "platform": 1001},
            {"id": 328086, "type": 1, "name": "過剰妄想少年 3", "name_cn": "",
                "infobox": "{{Infobox animanga/Manga\r\n|中文名= \r\n|别名={\r\n}\r\n|作者= ぴい\r\n}}", "platform": 1001},
        ]
        self.test_subject_file = "test_subject_data.jsonlines"
        self.test_subject_index = f"{self.test_subject_file}.index"
        self.test_relation_file = "test_relation_data.jsonlines"
        self.test_relation_index = f"{self.test_relation_file}.index"

        # 创建测试数据文件
        with open(self.test_subject_file, 'wb') as f:
            for item in self.sample_subject_data:
                line = json.dumps(item, ensure_ascii=False).encode(
                    'utf-8') + b'\n'
                f.write(line)

    def tearDown(self):
        """测试后清理"""
        for f in [self.test_subject_file, self.test_subject_index, self.test_relation_file, self.test_relation_index]:
            if os.path.exists(f):
                os.remove(f)

    def test_singleton_instance(self):
        """测试单例模式：相同文件路径返回同一实例"""
        reader1 = IndexedDataReader(self.test_subject_file)
        reader2 = IndexedDataReader(self.test_subject_file)
        self.assertIs(reader1, reader2)

    def test_init_without_index_file(self):
        """测试索引不存在时自动构建索引"""
        # 删除可能存在的索引文件
        if os.path.exists(self.test_subject_index):
            os.remove(self.test_subject_index)

        reader = IndexedDataReader(self.test_subject_file)

        # 验证索引结构正确
        expected_fields = {"id", "type", "name", "name_cn",
                           "subject_id", "name_cn_infobox", "aliases_infobox"}
        self.assertEqual(set(reader.index.keys()), expected_fields)

        # 验证 id 字段索引包含预期值
        self.assertIn(328150, reader.index["id"])
        self.assertIn(497, reader.index["id"])
        self.assertEqual(len(reader.index["id"][328150]), 1)
        self.assertEqual(len(reader.index["id"][497]), 1)

        # 验证 name_cn_infobox 和 aliases_infobox 被正确解析
        self.assertIn("新常态", reader.index["name_cn_infobox"])
        self.assertIn("人形电脑天使心", reader.index["name_cn_infobox"])
        self.assertIn("Chobits", reader.index["aliases_infobox"])

    def test_load_existing_index(self):
        """测试索引文件存在时正确加载"""
        # 先构建一次索引
        reader1 = IndexedDataReader(self.test_subject_file)
        original_index = reader1.index.copy()

        # 删除实例，重新加载
        del reader1
        reader2 = IndexedDataReader(self.test_subject_file)

        # 验证索引内容一致（未重建）
        self.assertEqual(reader2.index, original_index)

    @patch('os.path.getmtime')
    def test_rebuild_index_on_file_change(self, mock_getmtime):
        """测试当数据文件修改后自动重建索引"""
        # 构建索引
        reader = IndexedDataReader(self.test_subject_file)
        original_index = reader.index.copy()

        # 模拟文件被修改（mtime 变大）
        mock_getmtime.side_effect = lambda path: 999999999 if path == self.test_subject_file else 1000

        # 重新获取实例（触发重建）
        reader2 = IndexedDataReader(self.test_subject_file)

        # 验证索引被重建（内容不同）
        self.assertNotEqual(reader2.index, original_index)

    def test_get_data_by_query_single_field(self):
        """测试单字段查询：id"""
        reader = IndexedDataReader(self.test_subject_file)
        result = reader.get_data_by_query(id=497)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name_cn"], "人形电脑天使心")

    def test_get_data_by_query_multiple_fields(self):
        """测试多字段联合查询：id + type"""
        reader = IndexedDataReader(self.test_subject_file)
        result = reader.get_data_by_query(id=497, type=1)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name_cn"], "人形电脑天使心")

        # 查询不存在的组合
        result = reader.get_data_by_query(id=497, type=2)
        self.assertEqual(result, [])

    def test_get_data_by_query_field_not_in_index(self):
        """查询字段不在索引中 → 返回空"""
        reader = IndexedDataReader(self.test_subject_file)
        result = reader.get_data_by_query(nonexistent_field=123)
        self.assertEqual(result, [])

    def test_get_data_by_query_value_not_in_index(self):
        """查询值不在索引中 → 返回空"""
        reader = IndexedDataReader(self.test_subject_file)
        result = reader.get_data_by_query(id=999999999)
        self.assertEqual(result, [])

    def test_get_data_by_query_fulltext_search(self):
        """测试全文模糊搜索"""
        reader = IndexedDataReader(self.test_subject_file)

        # 搜索 "常态" → 应匹配 "新常态"
        result = reader.get_data_by_query("常态")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name_cn"], "新常态")

        # 搜索 "Chobits" → 应匹配别名
        result = reader.get_data_by_query("Chobits")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name_cn"], "人形电脑天使心")

        # 搜索 "米奇" → 应匹配 name_cn
        result = reader.get_data_by_query("米奇")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name_cn"], "米奇的房车")

        # 搜索不存在的词
        result = reader.get_data_by_query("不存在的词")
        self.assertEqual(result, [])

    def test_get_data_by_query_fulltext_search_multiple_matches(self):
        """全文搜索匹配多个字段"""
        # 添加一个新数据，让 name 和 name_cn 都包含 "test"
        extra_data = {"id": 999, "type": 1, "name": "test",
                      "name_cn": "测试", "infobox": "{{Infobox}}"}
        with open(self.test_subject_file, 'ab') as f:
            f.write(json.dumps(extra_data, ensure_ascii=False).encode(
                'utf-8') + b'\n')

        # 重新加载（会重建索引）
        reader = IndexedDataReader(self.test_subject_file)

        # 搜索 "test" → 应匹配 name="test" 和 name_cn="测试"（"测试"含"test"？不！）
        # 但 "test" 在 name 中，name_cn 中无 "test"，所以只匹配 name="test"
        result = reader.get_data_by_query("test")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "test")

    def test_get_data_by_query_fulltext_search_type_error(self):
        """全文搜索传入非字符串应报错"""
        reader = IndexedDataReader(self.test_subject_file)
        with self.assertRaises(TypeError):
            reader.get_data_by_query(123)

        with self.assertRaises(TypeError):
            reader.get_data_by_query("a", "b")  # 多参数

    def test_get_data_by_query_empty_query(self):
        """空查询返回空列表"""
        reader = IndexedDataReader(self.test_subject_file)
        result = reader.get_data_by_query()
        self.assertEqual(result, [])

    def test_build_index_with_empty_infobox(self):
        """测试 infobox 为空时仍能正确构建索引"""
        # 修改测试数据：让一个条目 infobox 为空
        with open(self.test_subject_file, 'w', encoding='utf-8') as f:
            data = {"id": 1000, "type": 1, "name": "空infobox",
                    "name_cn": "无别名", "infobox": ""}
            f.write(json.dumps(data, ensure_ascii=False) + '\n')

        reader = IndexedDataReader(self.test_subject_file)
        self.assertIn(1000, reader.index["id"])
        self.assertNotIn("无别名", reader.index["name_cn_infobox"])  # 不应被索引
        self.assertEqual(len(reader.index["aliases_infobox"]), 0)

    def test_build_index_with_invalid_json_line(self):
        """测试数据文件中存在非法 JSON 行时，不影响其他行索引构建"""
        # 在文件末尾追加一行非法 JSON
        with open(self.test_subject_file, 'ab') as f:
            f.write(b'{"id": 1001, "invalid":\n')  # 非法 JSON

        reader = IndexedDataReader(self.test_subject_file)
        # 验证合法数据仍被索引
        self.assertIn(328150, reader.index["id"])
        self.assertIn(497, reader.index["id"])
        # 验证非法行未被索引（id=1001 不存在）
        self.assertNotIn(1001, reader.index["id"])
        # 验证索引大小仍为 5（原始5条，非法行被跳过）
        self.assertEqual(len(reader.index["id"]), 5)

    def test_corrupted_index_file_triggers_rebuild(self):
        """测试损坏的索引文件会触发重建"""
        # 构建正常索引
        reader1 = IndexedDataReader(self.test_subject_file)
        original_index = reader1.index.copy()

        # 破坏索引文件
        with open(self.test_subject_index, 'wb') as f:
            f.write(b"this is not a pickle")

        # 重新加载
        reader2 = IndexedDataReader(self.test_subject_file)

        # 验证索引重建成功
        self.assertNotEqual(reader2.index, original_index)
        self.assertIn(497, reader2.index["id"])

    def test_file_not_found_raises_error(self):
        """测试数据文件不存在时抛出 FileNotFoundError"""
        with self.assertRaises(FileNotFoundError):
            IndexedDataReader("nonexistent_file.jsonlines")

    def test_update_offsets_index_is_deprecated(self):
        """测试 update_offsets_index 被标记为废弃（仅检查装饰器是否生效）"""
        reader = IndexedDataReader(self.test_subject_file)
        # 由于装饰器在 Python <3.11 下是空函数，我们无法直接捕获警告
        # 但我们可以测试它是否仍然存在且行为正常（不崩溃）
        try:
            reader.update_offsets_index()  # 不应崩溃
        except Exception as e:
            self.fail(f"update_offsets_index 应该不崩溃，但抛出了 {e}")

    def test_index_file_is_created_after_build(self):
        """测试索引文件在构建后被创建"""
        if os.path.exists(self.test_subject_index):
            os.remove(self.test_subject_index)

        reader = IndexedDataReader(self.test_subject_file)
        self.assertTrue(os.path.exists(self.test_subject_index))
        self.assertGreater(os.path.getsize(self.test_subject_index), 0)

    def test_mmap_read_correctly(self):
        """测试 _get_lines_by_offsets 正确读取数据"""
        reader = IndexedDataReader(self.test_subject_file)
        offsets = reader.index["id"][497]
        lines = reader._get_lines_by_offsets(offsets)
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["id"], 497)
        self.assertEqual(lines[0]["name_cn"], "人形电脑天使心")

    def test_get_data_by_query_with_int_and_str_id(self):
        """测试 id 可以是 int 或 str"""
        reader = IndexedDataReader(self.test_subject_file)
        result1 = reader.get_data_by_query(id=497)
        result2 = reader.get_data_by_query(id="497")
        self.assertEqual(len(result1), 1)
        self.assertEqual(len(result2), 1)
        self.assertEqual(result1[0], result2[0])
