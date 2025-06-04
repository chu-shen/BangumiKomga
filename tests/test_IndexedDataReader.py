import unittest
import os
from unittest.mock import patch, MagicMock, mock_open
# from tools.log import logger
from config.config import ARCHIVE_FILES_DIR
from bangumiArchive.indexedJsonlinesRead import IndexedDataReader
from bangumiArchive.archiveAutoupdater import update_index


# @unittest.skip("临时跳过测试")
class TestIndexedDataReader(unittest.TestCase):
    # TODO: 将覆盖率提升到100%
    def setUp(self):
        # update_index()
        self.subject_reader = IndexedDataReader(
            os.path.join(ARCHIVE_FILES_DIR, "subject.jsonlines"))
        self.relation_reader = IndexedDataReader(
            os.path.join(ARCHIVE_FILES_DIR, "subject-relations.jsonlines"))

    def test_date_by_index_str(self):
        result = self.subject_reader.get_data_by_id("104227", "id")[0]
        self.assertEqual(result["name_cn"], "我喜欢的人—高桥真短篇集")

    def test_date_by_index_int(self):
        result = self.subject_reader.get_data_by_id(104227, "id")[0]
        self.assertEqual(result["name_cn"], "我喜欢的人—高桥真短篇集")

    def tearDown(self):
        # 清理
        del self.subject_reader
        del self.relation_reader
