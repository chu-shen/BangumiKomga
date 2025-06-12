import unittest
from unittest.mock import MagicMock, patch
from tempfile import TemporaryDirectory
from unittest.mock import patch
from tools.log import logger
from tools.resort_search_results_list import resort_search_list, compute_name_score_by_fuzzy


class TestSearchResort(unittest.TestCase):
    def setUp(self):
        """设置测试环境"""
        self.data_source = MagicMock()
        self.mock_metadata = {
            "id": 1,
            "name": "Test Series",
            "series": True,
            "platform": 1,
            "infobox": [],
            "name_cn": ""
        }

    def test_threshold_filtering(self):
        """测试搜索结果排序器 - 阈值过滤"""
        results = [{"id": 1}]
        self.data_source.get_subject_metadata.return_value = self.mock_metadata
        filtered = resort_search_list("Test", results, 90, self.data_source)
        # 验证低分结果被过滤
        self.assertEqual(len(filtered), 0, "应过滤掉低于阈值的结果")

    def test_sorting_accuracy(self):
        """测试搜索结果排序器 - 排序准确性"""
        # 创建多个测试结果并验证排序顺序
        # 创建测试元数据集合
        from api.bangumi_model import SubjectPlatform
        metadata_set = [
            # 高分条目（完全匹配中文名）
            {
                "id": 1,
                "name": "English1",
                "series": True,
                "platform": SubjectPlatform.Comic.value,  # 明确使用枚举值
                "infobox": [],
                "name_cn": "中文匹配"
            },
            # 中等分数条目（部分匹配中文名）
            {
                "id": 2,
                "name": "English2",
                "series": True,
                "platform": SubjectPlatform.Comic.value,
                "infobox": [],
                "name_cn": "中文匹配集"
            },
            # 低分条目（别名匹配）
            {
                "id": 3,
                "name": "Base Name",
                "series": True,
                "platform": SubjectPlatform.Comic.value,
                # "中文件名" 与 "中文匹配" 模糊匹配
                "infobox": [{"key": "别名", "value": [{"v": "中文件名"}]}],
                "name_cn": ""
            }
        ]

        # 配置数据源返回
        def mock_get_metadata(manga_id):
            return metadata_set[manga_id - 1]
        self.data_source.get_subject_metadata.side_effect = mock_get_metadata

        # 构造测试输入
        test_results = [{"id": i+1} for i in range(3)]

        # 执行排序（降低阈值确保通过）
        sorted_results = resort_search_list(
            "中文匹配", test_results, 30, self.data_source)

        # 验证基础条件
        self.assertEqual(len(sorted_results), 3, "应保留所有符合平台和系列条件的条目")

        # 验证得分计算合理性
        self.assertGreater(sorted_results[0]["fuzzScore"], 80)  # 完全匹配中文名
        self.assertLess(sorted_results[2]["fuzzScore"], 70)     # 别名匹配得分较低

        # 验证排序稳定性
        scores = [item["fuzzScore"] for item in sorted_results]
        self.assertEqual(scores, sorted(scores, reverse=True), "得分应按降序排列")


class TestFuzzyNameScoring(unittest.TestCase):
    def test_exact_match(self):
        """测试模糊名称评分器 - 完全匹配"""
        self.assertEqual(compute_name_score_by_fuzzy(
            "Test", "", [], "Test"), 100)

    def test_chinese_name_priority(self):
        """测试模糊名称评分器 - 中文名优先级"""
        score = compute_name_score_by_fuzzy("English", "中文", [], "中文")
        self.assertEqual(score, 100)

    def test_aliases_scoring(self):
        """测试模糊名称评分器 - 别名匹配"""
        infobox = [{"key": "别名", "value": [{"v": "Alias1"}, {"v": "Alias2"}]}]
        score = compute_name_score_by_fuzzy("Base", "", infobox, "Alias2")
        self.assertGreater(score, 80)  # 根据实际fuzz结果调整
