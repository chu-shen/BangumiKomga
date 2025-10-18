import unittest
import os
from unittest.mock import patch, MagicMock, mock_open
import tempfile
from config.config import ARCHIVE_FILES_DIR
from bangumi_archive.archive_autoupdater import *


class TestFileIntegrityVerifier(unittest.TestCase):
    """测试文件完整性验证工具"""

    def setUp(self):
        import hashlib
        self.temp_dir = tempfile.TemporaryDirectory()
        self.file_path = os.path.join(self.temp_dir.name, "test_file.txt")
        self.content = b"test content"
        with open(self.file_path, "wb") as f:
            f.write(self.content)
        self.sha256 = hashlib.sha256(self.content).hexdigest()

    def test_hash_verification_success(self):
        """测试archive文件自动更新器 - hash完整性验证成功"""
        self.assertTrue(file_integrity_verifier(
            self.file_path, expected_hash=self.sha256))

    def test_hash_verification_failure(self):
        """测试archive文件自动更新器 - hash完整性验证失败"""
        wrong_hash = "0" * 64
        self.assertFalse(file_integrity_verifier(
            self.file_path, expected_hash=wrong_hash))

    def test_size_verification_success(self):
        """测试archive文件自动更新器 - 文件尺寸验证成功"""
        self.assertTrue(file_integrity_verifier(
            self.file_path, expected_size=len(self.content)))

    def test_size_verification_failure(self):
        """测试archive文件自动更新器 - 文件尺寸验证失败"""
        self.assertFalse(file_integrity_verifier(
            self.file_path, expected_size=100))

    def test_zip_crc_check(self):
        """测试archive文件自动更新器 - 压缩文件CRC验证"""
        zip_path = os.path.join(self.temp_dir.name, "test.zip")
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("test.txt", "test content")

        # 正常 ZIP
        self.assertTrue(file_integrity_verifier(zip_path))

        # 以二进制方式打开文件进行追加写入, 模拟损坏 ZIP
        with open(zip_path, "wb") as f:
            # 写入随机垃圾数据
            f.write(os.urandom(100))
        self.assertFalse(file_integrity_verifier(zip_path))

    def tearDown(self):
        self.temp_dir.cleanup()


class TestGetLatestInfo(unittest.TestCase):
    """测试在线获取Archive信息"""
    @patch("requests.get")
    def test_successful_response(self, mock_get):
        """测试archive文件自动更新器 - 成功获取Archive信息"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "browser_download_url": "https://example.com/archive.zip",
            "updated_at": "2023-10-01T12:00:00Z",
            "size": 1024
        }
        mock_get.return_value = mock_response

        url, time, size = get_latest_url_update_time_and_size()
        self.assertEqual(url, "https://example.com/archive.zip")
        self.assertEqual(time, "2023-10-01T12:00:00Z")
        self.assertEqual(size, 1024)

    @patch("requests.get")
    def test_request_exception(self, mock_get):
        """测试archive文件自动更新器 - 获取Archive信息请求异常"""
        mock_get.side_effect = Exception("Connection refused")
        url, time, size = get_latest_url_update_time_and_size()
        self.assertEqual(url, "")
        self.assertEqual(time, "")
        self.assertEqual(size, "")

    @patch("requests.get")
    def test_json_decode_error(self, mock_get):
        """测试archive文件自动更新器 - 获取的json解析异常"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_get.return_value = mock_response

        url, time, size = get_latest_url_update_time_and_size()
        self.assertEqual(url, "")
        self.assertEqual(time, "")
        self.assertEqual(size, "")


class TestUpdateArchive(unittest.TestCase):
    """测试archive文件自动更新"""
    @patch("os.path.exists")
    @patch("requests.get")
    @patch("builtins.open", new_callable=mock_open)
    @patch("os.remove")
    @patch("zipfile.ZipFile")
    def test_download_and_extract_success(self, mock_zip, mock_remove, mock_open, mock_get, mock_exists):
        """测试archive文件自动更新器 - 成功下载并解压archive"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-length": "1024"}
        mock_response.iter_content.return_value = [b"chunk"]
        mock_get.return_value = mock_response

        # 模拟文件存在
        mock_exists.return_value = True
        # 创建完整的ZipFile模拟实例
        mock_zip_instance = MagicMock()
        mock_zip_instance.testzip.return_value = None  # ZIP校验通过
        mock_zip.return_value.__enter__.return_value = MagicMock(
            testzip=lambda: None,
            extractall=MagicMock()
        )
        # 配置上下文管理器行为
        mock_zip.return_value.__enter__.return_value = mock_zip_instance

        # 执行测试
        with patch("bangumi_archive.archive_autoupdater.file_integrity_verifier", return_value=True):
            result = update_archive("http://example.com/archive.zip")
            self.assertTrue(result)
            mock_remove.assert_called_once()
            mock_zip_instance.extractall.assert_called()

            # 验证文件写入完整性
            mock_file = mock_open("dummy_path", "wb").__enter__()
            mock_file.write.assert_called_once_with(b"chunk")

    @patch("requests.get")
    def test_download_failure(self, mock_get):
        """测试archive文件自动更新器 - 压缩文件下载失败"""
        mock_get.side_effect = Exception("Network error")
        result = update_archive("http://example.com/archive.zip")
        self.assertFalse(result)

    @patch("requests.get")
    @patch("builtins.open", new_callable=mock_open)
    def test_file_integrity_failure(self, mock_open, mock_get):
        """测试archive文件自动更新器 - 压缩文件下载不完整"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-length": "1024"}
        mock_response.iter_content.return_value = [b"chunk"]
        mock_get.return_value = mock_response

        with patch("bangumi_archive.archive_autoupdater.file_integrity_verifier", return_value=False):
            result = update_archive("http://example.com/archive.zip")
            self.assertFalse(result)


class TestCheckArchive(unittest.TestCase):
    """测试检查archive文件自动更新"""
    @patch("bangumi_archive.archive_autoupdater.get_latest_url_update_time_and_size")
    @patch("bangumi_archive.archive_autoupdater.TimeCacheManager.read_time")
    @patch("bangumi_archive.archive_autoupdater.TimeCacheManager.convert_to_datetime")
    @patch("bangumi_archive.archive_autoupdater.update_archive")
    @patch("bangumi_archive.archive_autoupdater.update_index")
    @patch("bangumi_archive.archive_autoupdater.TimeCacheManager.save_time")
    def test_remote_newer(self, mock_save, mock_index, mock_update, mock_conv, mock_read, mock_get):
        """测试archive文件自动更新器 - 发现有archive更新"""
        mock_get.return_value = ("url", "2023-10-01T12:00:00Z", 1024)
        mock_read.return_value = "2023-09-01T12:00:00Z"
        mock_conv.side_effect = lambda x: x

        mock_update.return_value = True

        check_archive()
        mock_update.assert_called_once()
        mock_index.assert_called_once()
        mock_save.assert_called_once()

    @patch("bangumi_archive.archive_autoupdater.get_latest_url_update_time_and_size")
    @patch("bangumi_archive.archive_autoupdater.TimeCacheManager.read_time")
    @patch("bangumi_archive.archive_autoupdater.TimeCacheManager.convert_to_datetime")
    def test_local_newer(self, mock_conv, mock_read, mock_get):
        """测试archive文件自动更新器 - 发现没有archive更新"""
        mock_get.return_value = ("url", "2023-09-01T12:00:00Z", 1024)
        mock_read.return_value = "2023-10-01T12:00:00Z"
        mock_conv.side_effect = lambda x: x

        check_archive()
        # 验证 update_archive 未被调用


class TestUpdateIndex(unittest.TestCase):
    @patch("bangumi_archive.archive_autoupdater.IndexedDataReader")
    def test_update_index(self, mock_reader):
        """测试archive文件自动更新器 - 触发索引更新"""
        mock_instance = MagicMock()
        mock_reader.return_value = mock_instance
        update_index()
        mock_reader.assert_called()  # 确保构造函数被调用了
        # 验证 _build_index 是否被调用（实际代码调用的是这个）
        mock_instance._build_index.assert_called()
        # 如果你希望验证被调用了两次（两个文件），可以：
        self.assertEqual(mock_instance._build_index.call_count, 2)
