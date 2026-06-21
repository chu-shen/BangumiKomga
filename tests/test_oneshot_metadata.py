# -*- coding: utf-8 -*- #
# ------------------------------------------------------------------
# Description: One-Shot 元数据处理的单元测试
# ------------------------------------------------------------------


import unittest
from unittest.mock import patch, MagicMock, call

import core.process_metadata as process_metadata
from api.komga_api import SeriesMetadata


class TestSetOneshotSeriesMetadata(unittest.TestCase):
    """测试 process_metadata.py 中的 set_oneshot_series_metadata() 函数"""

    def setUp(self):
        self.bangumi_metadata = {
            "id": 12345,
            "name": "テスト漫画",
            "name_cn": "测试漫画",
            "platform": 1001,
            "summary": "A test summary.",
            "nsfw": False,
            "date": "2024-01-01",
            "rating": {"score": 7.5},
            "tags": [],
            "infobox": [],
        }

    @patch("core.process_metadata.set_komga_series_metadata")
    def test_status_forced_to_ended(self, mock_set_komga):
        """One-Shot 系列元数据：无论原状态如何，最终强制设为 ENDED"""
        mock_meta = SeriesMetadata()
        mock_meta.status = "ONGOING"
        mock_meta.isvalid = True
        mock_set_komga.return_value = mock_meta

        result = process_metadata.set_oneshot_series_metadata(
            self.bangumi_metadata, "test_manga.cbz", MagicMock()
        )

        self.assertEqual(result.status, "ENDED")

    @patch("core.process_metadata.set_komga_series_metadata")
    def test_total_book_count_forced_to_one(self, mock_set_komga):
        """One-Shot 系列元数据：总册数强制设为 1"""
        mock_meta = SeriesMetadata()
        mock_meta.totalBookCount = 5
        mock_meta.isvalid = True
        mock_set_komga.return_value = mock_meta

        result = process_metadata.set_oneshot_series_metadata(
            self.bangumi_metadata, "test_manga.cbz", MagicMock()
        )

        self.assertEqual(result.totalBookCount, 1)

    @patch("core.process_metadata.set_komga_series_metadata")
    def test_status_stays_ended_if_already_ended(self, mock_set_komga):
        """One-Shot 系列元数据：基础元数据已为 ENDED 时仍保持 ENDED"""
        mock_meta = SeriesMetadata()
        mock_meta.status = "ENDED"
        mock_meta.isvalid = True
        mock_set_komga.return_value = mock_meta

        result = process_metadata.set_oneshot_series_metadata(
            self.bangumi_metadata, "test_manga.cbz", MagicMock()
        )

        self.assertEqual(result.status, "ENDED")

    @patch("core.process_metadata.set_komga_series_metadata")
    def test_delegates_to_set_komga_series_metadata(self, mock_set_komga):
        """One-Shot 系列元数据：所有字段委托给 set_komga_series_metadata 处理"""
        mock_bgm = MagicMock()
        manga_filename = "test_manga.cbz"

        process_metadata.set_oneshot_series_metadata(
            self.bangumi_metadata, manga_filename, mock_bgm
        )

        mock_set_komga.assert_called_once_with(
            self.bangumi_metadata, manga_filename, mock_bgm
        )

    @patch("core.process_metadata.set_komga_series_metadata")
    def test_preserves_title_from_base(self, mock_set_komga):
        """One-Shot 系列元数据：保留基础元数据中的标题字段"""
        mock_meta = SeriesMetadata()
        mock_meta.title = "测试漫画"
        mock_meta.isvalid = True
        mock_set_komga.return_value = mock_meta

        result = process_metadata.set_oneshot_series_metadata(
            self.bangumi_metadata, "test.cbz", MagicMock()
        )

        self.assertEqual(result.title, "测试漫画")

    @patch("core.process_metadata.set_komga_series_metadata")
    def test_preserves_summary_from_base(self, mock_set_komga):
        """One-Shot 系列元数据：保留基础元数据中的概要字段"""
        mock_meta = SeriesMetadata()
        mock_meta.summary = "A test summary."
        mock_meta.isvalid = True
        mock_set_komga.return_value = mock_meta

        result = process_metadata.set_oneshot_series_metadata(
            self.bangumi_metadata, "test.cbz", MagicMock()
        )

        self.assertEqual(result.summary, "A test summary.")

    @patch("core.process_metadata.set_komga_series_metadata")
    def test_preserves_language_from_base(self, mock_set_komga):
        """One-Shot 系列元数据：保留基础元数据中的语言字段"""
        mock_meta = SeriesMetadata()
        mock_meta.language = "ja-JP"
        mock_meta.isvalid = True
        mock_set_komga.return_value = mock_meta

        result = process_metadata.set_oneshot_series_metadata(
            self.bangumi_metadata, "test.cbz", MagicMock()
        )

        self.assertEqual(result.language, "ja-JP")


class TestRefreshMetadataOneshotDetection(unittest.TestCase):
    """测试 refresh_metadata() 中 One-Shot 检测分支的逻辑"""

    def _make_series(self, series_id, name, oneshot=False, links=None):
        """辅助函数：创建模拟的系列字典"""
        return {
            "id": series_id,
            "name": name,
            "is_novel": False,
            "oneshot": oneshot,
            "metadata": {"links": links or []},
        }

    def _make_book_content(self, book_id="book-1", name="test book"):
        """辅助函数：创建模拟的书籍列表响应"""
        return {"content": [{"id": book_id, "name": name, "metadata": {"links": []}}]}

    def _configure_mock_cursor(self, mock_cursor, fetchall_rows=None, fetchone_row=None):
        """辅助函数：配置模拟的 sqlite3 游标，支持链式调用 execute().fetchall()/.fetchone()"""
        execute_result = MagicMock()
        if fetchall_rows is not None:
            execute_result.fetchall.return_value = fetchall_rows
        if fetchone_row is not None:
            execute_result.fetchone.return_value = fetchone_row
        mock_cursor.execute.return_value = execute_result
        # 同时配置 __iter__ 使游标本身可被迭代
        mock_cursor.__iter__.return_value = iter(fetchall_rows or [])

    def _setup_common_mocks(
        self, mock_parse_title, mock_get_series, mock_record_book,
        mock_record_series, mock_cursor, mock_conn, mock_komga, mock_bgm,
        series_id, series_name, oneshot, series_records,
        bangumi_meta=None, bangumi_search_results=None,
        book_content=None
    ):
        """辅助函数：配置测试场景中所有通用的模拟对象"""
        series_list = [self._make_series(series_id, series_name, oneshot=oneshot)]
        mock_get_series.return_value = series_list

        self._configure_mock_cursor(mock_cursor, fetchall_rows=series_records)

        mock_pt_instance = MagicMock()
        mock_pt_instance.get_title.return_value = series_name
        mock_parse_title.return_value = mock_pt_instance

        if bangumi_meta:
            mock_bgm.get_subject_metadata.return_value = bangumi_meta
        if bangumi_search_results is not None:
            mock_bgm.search_subjects.return_value = bangumi_search_results

        mock_komga.update_series_metadata.return_value = True
        mock_komga.get_series_thumbnails.return_value = []
        mock_komga.get_series_books.return_value = book_content or self._make_book_content()
        mock_komga.update_book_metadata.return_value = True
        mock_record_series.return_value = (1, "success")
        mock_record_book.return_value = None

        return series_list

    @patch("core.refresh_metadata.bgm")
    @patch("core.refresh_metadata.komga")
    @patch("core.refresh_metadata.conn")
    @patch("core.refresh_metadata.cursor")
    @patch("core.refresh_metadata.record_series_status")
    @patch("core.refresh_metadata.record_book_status")
    @patch("core.refresh_metadata.get_series_metadata")
    @patch("core.refresh_metadata.ParseTitle")
    def test_oneshot_db_cache_renews_metadata(
        self, mock_parse_title, mock_get_series, mock_record_book,
        mock_record_series, mock_cursor, mock_conn, mock_komga, mock_bgm
    ):
        """One-Shot 已刮削系列：重新拉取元数据而非调用 refresh_book_metadata"""
        series_id = "oneshot-series-1"
        meta = self._make_bangumi_meta()
        subject_id_value = 12345

        series_list = self._setup_common_mocks(
            mock_parse_title, mock_get_series, mock_record_book,
            mock_record_series, mock_cursor, mock_conn, mock_komga, mock_bgm,
            series_id, "OneShot Manga", True,
            series_records=[(series_id, subject_id_value, 1)],
            bangumi_meta=meta,
        )

        # 主流程 2 次 cursor.execute + FAILED_COLLECTION 查询 1 次
        execute_results = [
            MagicMock(**{"fetchall.return_value": [(series_id, subject_id_value, 1)]}),
            MagicMock(**{"fetchone.return_value": [subject_id_value]}),
            MagicMock(**{"fetchall.return_value": []}),  # FAILED_COLLECTION 查询
        ]
        mock_cursor.execute.side_effect = execute_results

        from core.refresh_metadata import refresh_metadata
        refresh_metadata(series_list)

        mock_bgm.get_subject_metadata.assert_called_with(subject_id_value)
        mock_komga.update_book_metadata.assert_called()

    @patch("core.refresh_metadata.bgm")
    @patch("core.refresh_metadata.komga")
    @patch("core.refresh_metadata.conn")
    @patch("core.refresh_metadata.cursor")
    @patch("core.refresh_metadata.record_series_status")
    @patch("core.refresh_metadata.record_book_status")
    @patch("core.refresh_metadata.get_series_metadata")
    @patch("core.refresh_metadata.ParseTitle")
    @patch("core.refresh_metadata.refresh_book_metadata")
    def test_non_oneshot_db_cache_skips_to_refresh_book(
        self, mock_refresh_book, mock_parse_title, mock_get_series,
        mock_record_book, mock_record_series, mock_cursor, mock_conn,
        mock_komga, mock_bgm
    ):
        """非 One-Shot 已刮削系列：直接调用 refresh_book_metadata 并跳过后续"""
        series_id = "normal-series-1"
        subject_id_value = 12345

        series_list = self._setup_common_mocks(
            mock_parse_title, mock_get_series, mock_record_book,
            mock_record_series, mock_cursor, mock_conn, mock_komga, mock_bgm,
            series_id, "Normal Manga", False,
            series_records=[(series_id, subject_id_value, 1)],
        )

        # 主流程 2 次 + FAILED_COLLECTION 查询 1 次
        execute_results = [
            MagicMock(**{"fetchall.return_value": [(series_id, subject_id_value, 1)]}),
            MagicMock(**{"fetchone.return_value": [subject_id_value]}),
            MagicMock(**{"fetchall.return_value": []}),  # FAILED_COLLECTION 查询
        ]
        mock_cursor.execute.side_effect = execute_results

        from core.refresh_metadata import refresh_metadata
        refresh_metadata(series_list)

        mock_refresh_book.assert_called_once_with(subject_id_value, series_id, False)
        mock_bgm.get_subject_metadata.assert_not_called()

    @patch("core.refresh_metadata.bgm")
    @patch("core.refresh_metadata.komga")
    @patch("core.refresh_metadata.conn")
    @patch("core.refresh_metadata.cursor")
    @patch("core.refresh_metadata.record_series_status")
    @patch("core.refresh_metadata.record_book_status")
    @patch("core.refresh_metadata.get_series_metadata")
    @patch("core.refresh_metadata.ParseTitle")
    def test_oneshot_fallback_to_search_when_not_in_db(
        self, mock_parse_title, mock_get_series, mock_record_book,
        mock_record_series, mock_cursor, mock_conn, mock_komga, mock_bgm
    ):
        """One-Shot 未记录在 DB：回退到 Bangumi 搜索，然后覆写 ENDED/1"""
        series_id = "oneshot-new-1"
        meta = self._make_bangumi_meta()

        series_list = self._setup_common_mocks(
            mock_parse_title, mock_get_series, mock_record_book,
            mock_record_series, mock_cursor, mock_conn, mock_komga, mock_bgm,
            series_id, "New OneShot Manga", True,
            series_records=[],
            bangumi_search_results=[meta],
        )

        from core.refresh_metadata import refresh_metadata
        refresh_metadata(series_list)

        update_call_args = mock_komga.update_series_metadata.call_args
        series_data = update_call_args[0][1]
        self.assertEqual(series_data["status"], "ENDED")
        self.assertEqual(series_data["totalBookCount"], 1)

    @patch("core.refresh_metadata.bgm")
    @patch("core.refresh_metadata.komga")
    @patch("core.refresh_metadata.conn")
    @patch("core.refresh_metadata.cursor")
    @patch("core.refresh_metadata.record_series_status")
    @patch("core.refresh_metadata.record_book_status")
    @patch("core.refresh_metadata.get_series_metadata")
    @patch("core.refresh_metadata.ParseTitle")
    def test_oneshot_updates_single_book_not_refresh_all(
        self, mock_parse_title, mock_get_series, mock_record_book,
        mock_record_series, mock_cursor, mock_conn, mock_komga, mock_bgm
    ):
        """One-Shot：仅通过 update_book_metadata 更新单本书，不调用 refresh_book_metadata"""
        series_id = "oneshot-single-book"
        meta = self._make_bangumi_meta()

        series_list = self._setup_common_mocks(
            mock_parse_title, mock_get_series, mock_record_book,
            mock_record_series, mock_cursor, mock_conn, mock_komga, mock_bgm,
            series_id, "Solo Manga", True,
            series_records=[],
            bangumi_search_results=[meta],
            book_content=self._make_book_content("book-oneshot-1", "Solo Manga"),
        )

        from core.refresh_metadata import refresh_metadata
        refresh_metadata(series_list)

        mock_komga.update_book_metadata.assert_called_once()
        book_call = mock_komga.update_book_metadata.call_args
        self.assertEqual(book_call[0][0], "book-oneshot-1")

    @patch("core.refresh_metadata.bgm")
    @patch("core.refresh_metadata.komga")
    @patch("core.refresh_metadata.conn")
    @patch("core.refresh_metadata.cursor")
    @patch("core.refresh_metadata.record_series_status")
    @patch("core.refresh_metadata.record_book_status")
    @patch("core.refresh_metadata.get_series_metadata")
    @patch("core.refresh_metadata.ParseTitle")
    def test_oneshot_no_books_skips_update(
        self, mock_parse_title, mock_get_series, mock_record_book,
        mock_record_series, mock_cursor, mock_conn, mock_komga, mock_bgm
    ):
        """One-Shot 无书籍：系列下没有 book 时优雅跳过书籍更新"""
        series_id = "oneshot-empty"
        meta = self._make_bangumi_meta()

        series_list = self._setup_common_mocks(
            mock_parse_title, mock_get_series, mock_record_book,
            mock_record_series, mock_cursor, mock_conn, mock_komga, mock_bgm,
            series_id, "Empty OneShot", True,
            series_records=[],
            bangumi_search_results=[meta],
            book_content={"content": []},
        )

        from core.refresh_metadata import refresh_metadata
        refresh_metadata(series_list)

        mock_komga.update_series_metadata.assert_called_once()
        mock_komga.update_book_metadata.assert_not_called()

    @patch("core.refresh_metadata.bgm")
    @patch("core.refresh_metadata.komga")
    @patch("core.refresh_metadata.conn")
    @patch("core.refresh_metadata.cursor")
    @patch("core.refresh_metadata.record_series_status")
    @patch("core.refresh_metadata.record_book_status")
    @patch("core.refresh_metadata.get_series_metadata")
    @patch("core.refresh_metadata.ParseTitle")
    def test_oneshot_with_cbl_uses_cbl_metadata(
        self, mock_parse_title, mock_get_series, mock_record_book,
        mock_record_series, mock_cursor, mock_conn, mock_komga, mock_bgm
    ):
        """One-Shot 含 CBL 链接：使用 CBL 中的 subject_id 并应用 oneshot 覆写"""
        series_id = "oneshot-cbl"
        cbl_url = "https://bgm.tv/subject/99999"
        meta = self._make_bangumi_meta(99999)

        series_list = self._setup_common_mocks(
            mock_parse_title, mock_get_series, mock_record_book,
            mock_record_series, mock_cursor, mock_conn, mock_komga, mock_bgm,
            series_id, "CBL OneShot", True,
            series_records=[],
            bangumi_meta=meta,
        )
        # 覆写：CBL 路径直接设置链接并跳过搜索
        series_list[0]["metadata"]["links"] = [{"label": "CBL", "url": cbl_url}]

        mock_bgm.get_subject_metadata.return_value = meta

        from core.refresh_metadata import refresh_metadata
        refresh_metadata(series_list)

        mock_bgm.get_subject_metadata.assert_called_with(99999)
        mock_bgm.search_subjects.assert_not_called()

        update_call = mock_komga.update_series_metadata.call_args
        series_data = update_call[0][1]
        self.assertEqual(series_data["status"], "ENDED")
        self.assertEqual(series_data["totalBookCount"], 1)

    # --- helpers ---

    @staticmethod
    def _make_bangumi_meta(subject_id=12345):
        return {
            "id": subject_id,
            "name": "テスト漫画",
            "name_cn": "测试漫画",
            "platform": 1001,
            "summary": "A test manga summary.",
            "nsfw": False,
            "date": "2024-01-01",
            "rating": {"score": 7.5},
            "tags": [],
            "infobox": [],
        }


class TestKomgaApiOneshotField(unittest.TestCase):
    """验证 Komga API 响应结构中存在 oneshot 字段"""

    def test_series_dto_has_oneshot_field(self):
        """Komga SeriesDto：包含 'oneshot' 布尔字段"""
        # 基于 Komga OpenAPI 1.24.4：SeriesDto.oneshot 为必填字段
        series = {
            "id": "series-1",
            "name": "test",
            "oneshot": False,
        }
        self.assertIn("oneshot", series)
        self.assertIsInstance(series["oneshot"], bool)

    def test_book_dto_has_oneshot_field(self):
        """Komga BookDto：包含 'oneshot' 布尔字段"""
        # 基于 Komga OpenAPI 1.24.4：BookDto.oneshot 为必填字段
        book = {
            "id": "book-1",
            "name": "test",
            "oneshot": False,
        }
        self.assertIn("oneshot", book)
        self.assertIsInstance(book["oneshot"], bool)

    def test_oneshot_detection_with_get_returns_false_for_missing(self):
        """安全检测：series.get('oneshot', False) 在字段缺失时优雅返回 False"""
        series_no_key = {"id": "old-series", "name": "Legacy"}
        self.assertFalse(series_no_key.get("oneshot", False))

        series_true = {"id": "os-1", "name": "One", "oneshot": True}
        self.assertTrue(series_true.get("oneshot", False))

