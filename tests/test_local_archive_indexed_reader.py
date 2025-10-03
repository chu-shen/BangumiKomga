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
        # 创建一个不会自动删除的临时文件
        tmp = tempfile.NamedTemporaryFile(
            mode='w', delete=False, suffix='.jsonl')
        self.test_subject_file = tmp.name  # 保存路径
        tmp.close()  # 关闭文件句柄，但文件保留

        self.sample_subject_data = [
            {"id": 328150, "type": 1, "name": "ニューノーマル", "name_cn": "新常态",
                "infobox": "{{Infobox animanga/Manga\r\n|中文名= 新常态\r\n|别名={\r\n[你和我的嘴唇]\r\n[未来的恋爱必须戴口罩]\r\n[New Normal]\r\n}\r\n|出版社= ファンギルド\r\n|价格= \r\n|其他出版社= \r\n|连载杂志= \r\n|发售日= 2021-07-19\r\n|册数= \r\n|页数= \r\n|话数= \r\n|ISBN= \r\n|其他= \r\n|作者= 相原瑛人\r\n|开始= 2020-12-18\r\n}}", "platform": 1001},
            {"id": 241596, "type": 2, "name": "Mickey's Trailer", "name_cn": "米奇的房车",
                "infobox": "{{Infobox animanga/Anime\r\n|中文名= 米奇的房车\r\n|别名={\r\n}\r\n|上映年度= 1938-05-06\r\n|片长= 7分钟\r\n}}", "platform": 0},
            {"id": 497, "type": 1, "name": "ちょびっツ", "name_cn": "人形电脑天使心",
                "infobox": "{{Infobox animanga/Manga\r\n|中文名= 人形电脑天使心\r\n|别名={\r\n[Chobits]\r\n}\r\n|出版社= 講談社\r\n}}", "platform": 1001},
            {"id": 252236, "type": 1, "name": "GREASEBERRIES 2", "name_cn": "",
                "infobox": "{{Infobox animanga/Manga\r\n|中文名= \r\n|别名={\r\n}\r\n|作者= 士郎正宗\r\n}}", "platform": 1001},
            {"id": 328086, "type": 1, "name": "過剰妄想少年 3", "name_cn": "",
                "infobox": "{{Infobox animanga/Manga\r\n|中文名= \r\n|别名={\r\n}\r\n|作者= ぴい\r\n}}", "platform": 1001},
        ]

        # 用 self.sample_subject_data 写入测试文件
        self.test_subject_file = "test_subject_data.jsonl"  # 统一后缀为 .jsonl
        self.test_subject_index = f"{self.test_subject_file}.index"
        self.test_relation_file = "test_relation_data.jsonl"
        self.test_relation_index = f"{self.test_relation_file}.index"

        # 创建测试数据文件
        with open(self.test_subject_file, 'w', encoding='utf-8') as f:
            for item in self.sample_subject_data:  # 使用 self.sample_subject_data
                f.write(json.dumps(item, ensure_ascii=False,
                        separators=(',', ':')) + '\n')

    def tearDown(self):
        """测试后清理"""
        files_to_clean = [
            self.test_subject_file, self.test_subject_index,
            self.test_relation_file, self.test_relation_index
        ]
        for f in files_to_clean:
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
        # 构建索引（使用原始数据）
        reader = IndexedDataReader(self.test_subject_file)
        original_index = reader.index.copy()

        # 验证原始状态
        self.assertEqual(len(original_index["id"]), 5)

        # 模拟文件被修改（mtime 变大）
        mock_getmtime.side_effect = lambda path: 999999999 if path == self.test_subject_file else 1000

        # 添加一条新数据到文件中
        new_data = {"id": 8888, "type": 1, "name": "新数据",
                    "name_cn": "新增", "infobox": ""}
        with open(self.test_subject_file, 'ab') as f:
            f.write(json.dumps(new_data, ensure_ascii=False,
                    separators=(',', ':')).encode('utf-8') + b'\n')
            f.flush()

        # 验证写入成功
        with open(self.test_subject_file, 'rb') as f:
            lines = f.readlines()
            last_line = lines[-1].decode('utf-8').strip()
            self.assertEqual(
                last_line, '{"id":8888,"type":1,"name":"新数据","name_cn":"新增","infobox":""}')

        if self.test_subject_file in IndexedDataReader._instance:
            del IndexedDataReader._instance[self.test_subject_file]

        # 重新获取实例（强制重建）
        reader2 = IndexedDataReader(self.test_subject_file)

        # 验证新数据被索引
        self.assertIn(8888, reader2.index["id"])
        self.assertEqual(len(reader2.index["id"]), len(
            original_index["id"]) + 1)

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
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.jsonl') as f:
            temp_file_path = f.name
        try:
            # 写入原始数据（使用 self.sample_subject_data）
            with open(temp_file_path, 'w', encoding='utf-8') as f:
                for item in self.sample_subject_data:
                    f.write(json.dumps(item, ensure_ascii=False,
                            separators=(',', ':')) + '\n')

            # 追加一条新数据（包含 "test"）
            extra_data = {"id": 999, "type": 1, "name": "test",
                          "name_cn": "测试", "infobox": "{{Infobox}}"}
            with open(temp_file_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(extra_data, ensure_ascii=False,
                        separators=(',', ':')) + '\n')

            reader = IndexedDataReader(temp_file_path)
            result = reader.get_data_by_query("test")  # 全文模糊搜索

            # 验证：应该只匹配到 name="test" 的那一项
            # 注意：name_cn="测试" 不包含 "test"，所以不会被匹配
            # "test" 是英文，只匹配 name 字段中的 "test"
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]["name"], "test")

        finally:
            os.unlink(temp_file_path)

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
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.jsonlines') as f:
            temp_file_path = f.name

        try:
            data = {"id": 1000, "type": 1, "name": "空infobox",
                    "name_cn": "无别名", "infobox": ""}
            with open(temp_file_path, 'w', encoding='utf-8') as f:
                f.write(json.dumps(data, ensure_ascii=False) + '\n')

            reader = IndexedDataReader(temp_file_path)

            self.assertIn(1000, reader.index["id"])
            self.assertNotIn("无别名", reader.index["name_cn_infobox"])
            self.assertEqual(len(reader.index["aliases_infobox"]), 0)

        finally:
            os.unlink(temp_file_path)

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

    @patch('bangumi_archive.local_archive_indexed_reader.logger')
    def test_corrupted_index_file_triggers_rebuild(self, mock_logger):
        """测试损坏的索引文件会触发重建"""
        # 构建正常索引
        reader1 = IndexedDataReader(self.test_subject_file)
        original_index = reader1.index.copy()

        # 破坏索引文件：写入空文件 → 触发 EOFError
        with open(self.test_subject_index, 'wb') as f:
            pass  # 清空文件

        # 清除单例缓存，强制重建实例
        IndexedDataReader._instance.clear()

        # 重新加载
        reader2 = IndexedDataReader(self.test_subject_file)

        # 验证重建流程被触发
        for call in mock_logger.error.call_args_list:
            print(call)
        for call in mock_logger.info.call_args_list:
            print(call)

        mock_logger.error.assert_any_call(
            f"索引文件为空: {self.test_subject_index}"
        )
        mock_logger.info.assert_any_call(
            f"开始构建索引: {self.test_subject_file}"
        )

        # 验证重建成功
        self.assertEqual(reader2.index, original_index)
        self.assertIn(497, reader2.index["id"])
        self.assertEqual(reader2.get_data_by_query(
            id=497)[0]["name_cn"], "人形电脑天使心")

    def test_file_not_found_raises_error(self):
        """测试数据文件不存在时抛出 FileNotFoundError"""
        with self.assertRaises(FileNotFoundError):
            IndexedDataReader("nonexistent_file.jsonlines")

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
        self.assertEqual(len(result2), 0)
