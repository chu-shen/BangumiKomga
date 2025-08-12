import unittest
import json
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from tools.log import logger
from tools.cache_time import TimeCacheManager


class TestTimeCacheManager(unittest.TestCase):
    def setUp(self):
        """设置测试环境"""
        self.temp_dir = TemporaryDirectory()
        self.test_file = Path(self.temp_dir.name) / "cache.json"
        self.default_time = "1970-01-01T00:00:00Z"

    def tearDown(self):
        """清理测试环境"""
        self.temp_dir.cleanup()

    def test_read_time_file_exists_with_valid_content(self):
        """测试时间缓存管理器 - 读取有效缓存文件"""
        # 准备测试数据
        test_time = "2023-10-01T12:30:45Z"
        with open(self.test_file, 'w') as f:
            json.dump({"last_updated": test_time}, f)

        # 执行测试
        result = TimeCacheManager.read_time(str(self.test_file))
        self.assertEqual(result, test_time)

    def test_read_time_file_exists_missing_key(self):
        """测试时间缓存管理器 - 读取缺少关键字段的缓存文件"""
        # 准备测试数据
        with open(self.test_file, 'w') as f:
            json.dump({}, f)

        # 执行测试
        result = TimeCacheManager.read_time(str(self.test_file))
        self.assertEqual(result, self.default_time)

    def test_read_time_file_not_found(self):
        """测试时间缓存管理器 - 文件不存在的情况"""
        non_existent_file = str(Path(self.temp_dir.name) / "nonexistent.json")

        with self.assertLogs(logger, level='WARNING') as cm:
            result = TimeCacheManager.read_time(non_existent_file)
            self.assertEqual(result, self.default_time)
            self.assertIn("不存在，使用默认时间", cm.output[0])

    def test_read_time_invalid_json(self):
        """测试时间缓存管理器 - 无效的JSON文件"""
        # 准备测试数据
        with open(self.test_file, 'w') as f:
            f.write("invalid json")

        with self.assertLogs(logger, level='WARNING') as cm:
            result = TimeCacheManager.read_time(str(self.test_file))
            self.assertEqual(result, self.default_time)
            self.assertIn("解析失败", cm.output[0])

    def test_save_time_creates_file(self):
        """测试时间缓存管理器 - 创建新缓存"""
        test_time = "2023-10-01T12:30:45Z"
        TimeCacheManager.save_time(str(self.test_file), test_time)

        # 验证文件存在且内容正确
        self.assertTrue(self.test_file.exists())
        with open(self.test_file, 'r') as f:
            data = json.load(f)
            self.assertEqual(data["last_updated"], test_time)

    def test_save_time_overwrites_existing(self):
        """测试时间缓存管理器 - 覆盖已有缓存"""
        # 初始写入
        initial_time = "2023-01-01T00:00:00Z"
        with open(self.test_file, 'w') as f:
            json.dump({"last_updated": initial_time}, f)

        # 覆盖写入
        new_time = "2023-10-01T12:30:45Z"
        TimeCacheManager.save_time(str(self.test_file), new_time)

        # 验证内容更新
        with open(self.test_file, 'r') as f:
            data = json.load(f)
            self.assertEqual(data["last_updated"], new_time)

    def test_convert_to_datetime_valid_format(self):
        """测试时间缓存管理器 - 有效时间格式转换"""
        time_str = "2023-10-01T12:30:45Z"
        result = TimeCacheManager.convert_to_datetime(time_str)

        self.assertIsNotNone(result)
        # 验证时区转换
        expected = datetime.fromisoformat("2023-10-01T12:30:45+00:00")
        self.assertEqual(result, expected)

    def test_convert_to_datetime_invalid_format(self):
        """测试时间缓存管理器 - 无效时间格式"""
        time_str = "invalid-time-format"

        with self.assertLogs(logger, level='WARNING') as cm:
            result = TimeCacheManager.convert_to_datetime(time_str)
            self.assertIsNone(result)
            self.assertIn("获取失败", cm.output[0])

    def test_convert_to_datetime_no_timezone(self):
        """测试时间缓存管理器 - 无时区信息的转换"""
        time_str = "2023-10-01T12:30:45"
        result = TimeCacheManager.convert_to_datetime(time_str)

        self.assertIsNotNone(result)
        # 验证默认时区处理
        expected = datetime.fromisoformat(time_str).replace(tzinfo=None)
        self.assertEqual(result.replace(tzinfo=None), expected)
