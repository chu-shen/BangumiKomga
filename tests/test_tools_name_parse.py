import unittest
import re
from unittest.mock import mock_open, patch
from tools.get_number import *
from tools.get_title import *


class TestNumberParsingFunctions(unittest.TestCase):
    def test_get_number_with_prefix(self):
        # 测试卷/章前缀解析
        self.assertEqual(get_number_with_prefix(
            "vol.12"), (12.0, NumberType.VOLUME))
        self.assertEqual(get_number_with_prefix(
            "Chap.5"), (5.0, NumberType.CHAPTER))
        self.assertEqual(get_number_with_prefix(
            "VOL.08"), (8.0, NumberType.VOLUME))
        self.assertEqual(get_number_with_prefix(
            "chap.007"), (7.0, NumberType.CHAPTER))
        self.assertEqual(get_number_with_prefix(
            "no_prefix"), (None, NumberType.NONE))
        self.assertEqual(get_number_with_prefix(
            "vol."), (None, NumberType.NONE))
        self.assertEqual(get_number_with_prefix(
            "vol.xx"), (None, NumberType.NONE))
        self.assertEqual(get_number_with_prefix(
            "vol.12.3"), (12.0, NumberType.VOLUME))

    def test_roman_to_integer(self):
        # 测试罗马数字转换
        self.assertEqual(roman_to_integer("III"), 3)
        self.assertEqual(roman_to_integer("IX"), 9)
        self.assertEqual(roman_to_integer("XLII"), 42)
        self.assertEqual(roman_to_integer("MCMXCIV"), 1994)
        self.assertEqual(roman_to_integer("MMXXIII"), 2023)
        # 测试无效输入
        # FIXME
        # self.assertEqual(roman_to_integer("IIII"), None)  # 超过3次重复
        # self.assertEqual(roman_to_integer("VV"), None)    # 无效组合
        # self.assertEqual(roman_to_integer("ABC"), None)   # 非罗马数字

    def test_get_roman_number(self):
        # 测试罗马数字提取
        self.assertEqual(get_roman_number("Part II"), (2, NumberType.NORMAL))
        self.assertEqual(get_roman_number("123IV456"), (4, NumberType.NORMAL))
        self.assertEqual(get_roman_number("XLVIII"), (48, NumberType.NORMAL))
        # 测试边界条件
        self.assertEqual(get_roman_number("I"), (1, NumberType.NORMAL))
        self.assertEqual(get_roman_number("M"), (1000, NumberType.NORMAL))
        # 测试无效情况
        # FIXME
        # self.assertEqual(get_roman_number("IIX"), (None, NumberType.NONE))
        self.assertEqual(get_roman_number("AIXB"), (None, NumberType.NONE))
        self.assertEqual(get_roman_number("123"), (None, NumberType.NONE))
        # self.assertEqual(get_roman_number("XXL"), (None, NumberType.NONE))

    def test_normal_numbers(self):
        # 测试普通数字解析
        self.assertEqual(normal("price 12.99"), (12.99, NumberType.NORMAL))
        self.assertEqual(normal("year 2023"), (2023, NumberType.NORMAL))
        # 测试边界条件
        self.assertEqual(normal("0"), (0, NumberType.NORMAL))
        self.assertEqual(normal("0.0"), (0.0, NumberType.NORMAL))
        self.assertEqual(normal("9.999"), (9.999, NumberType.NORMAL))
        # 测试无效情况
        self.assertEqual(normal("abc"), (None, NumberType.NONE))
        # FIXME
        # self.assertEqual(normal("12.34.56"), (None, NumberType.NONE))

    def test_get_number_priority(self):
        # 测试解析优先级：前缀 > 罗马数字 > 普通数字
        self.assertEqual(get_number("vol.3 chap.5"), (3.0, NumberType.VOLUME))
        self.assertEqual(get_number("part IX"), (9, NumberType.NORMAL))
        self.assertEqual(get_number("chapter 12.5"), (12.5, NumberType.NORMAL))
        self.assertEqual(get_number("10-5"), (10.5, NumberType.NORMAL))


class TestTextProcessingFunctions(unittest.TestCase):
    def test_split_words(self):
        self.assertEqual(
            split_words("[漫画] [测试-1] [标签]"),
            ['漫画', '测试-1', '标签']
        )
        self.assertEqual(
            split_words("[ツガノガク] [涼宮春日的憂鬱]"),
            ['ツガノガク', '涼宮春日的憂鬱']
        )
        self.assertEqual(
            split_words("[标签A][标签B][标签C]"),
            ['标签A', '标签B', '标签C']
        )
        self.assertEqual(
            split_words("无括号内容"),
            ['无括号内容']
        )
        self.assertEqual(
            split_words("[空]内容[标签]"),
            ['空', '内容', '标签']
        )

    def test_remove_punctuation(self):
        self.assertEqual(remove_punctuation("!!test!!"), "test")
        self.assertEqual(remove_punctuation("##123##"), "123")
        self.assertEqual(remove_punctuation("!@#$%^&*()"), "")
        self.assertEqual(remove_punctuation(
            "no-punctuation"), "no-punctuation")

    def test_check_string_with_x(self):
        self.assertTrue(check_string_with_x("作者x作者2"))
        self.assertTrue(check_string_with_x("name×name2"))
        self.assertTrue(check_string_with_x("group&member"))
        self.assertFalse(check_string_with_x("纯中文"))  # 无特殊符号
        self.assertTrue(check_string_with_x("test_string1_×_test_string2"))
        self.assertTrue(check_string_with_x("test × string"))
        self.assertTrue(check_string_with_x("test×string"))  # x前后有字母

    def test_format_string(self):
        self.assertEqual(format_string("16-5"), "16.5")
        self.assertEqual(format_string("1_2_3"), "1.2.3")
        self.assertEqual(format_string("no.changes"), "no.changes")


class TestFileOperations(unittest.TestCase):
    @patch('builtins.open', new_callable=mock_open, read_data="line1\nline2\nline3")
    def test_read_corpus(self, mock_file):
        result = read_corpus("dummy_path")
        self.assertEqual(result, ["line1", "line2", "line3"])
        mock_file.assert_called_once_with("dummy_path", "r", encoding="utf-8")

    def test_build_vocabulary(self):
        vocab = build_vocabulary(["Comic", "Artbook", "汉化"])
        self.assertEqual(vocab, {"comic", "artbook", "汉化"})

    @patch('builtins.open', side_effect=FileNotFoundError)
    def test_missing_corpus_file(self, mock_file):
        with self.assertRaises(FileNotFoundError):
            read_corpus("invalid_path")


class TestParseTitle(unittest.TestCase):
    def setUp(self):
        self.parser = ParseTitle()

    def test_get_title(self):
        # 测试常用词汇过滤

        # 测试人名过滤
        self.assertEqual(
            self.parser.get_title("[作者x作者2] [漫画标题]"),
            "漫画标题"
        )
        # 测试无过滤情况
        self.assertEqual(
            self.parser.get_title("[非过滤词] [标题]"),
            "非过滤词"
        )
        self.assertEqual(
            self.parser.get_title("[漫画] [测试标题]"),
            "测试标题"
        )
        self.assertEqual(
            self.parser.get_title("[comic] [测试标题]"),
            "测试标题"
        )
