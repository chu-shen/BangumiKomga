import re
from zhconv import convert


class NumberType:
    VOLUME = "volume"
    CHAPTER = "chapter"
    NORMAL = "normal"
    NONE = "none"


class FileNameParser:
    # TODO: 实现其他字段的提取
    def __init__(self):
        self.corpus = []
        self.vocabulary = set()
        self.load_resources()

    def load_resources(self):
        self.corpus = self.read_corpus(
            "corpus/Japanese_Names_Corpus（18W）.txt") + self.read_corpus("corpus/bangumi_person.txt")
        self.vocabulary = self.build_vocabulary(
            ["comic", "comics", "artbook", "artbooks", "汉化", "全彩版", "青文"])

    @staticmethod
    def read_corpus(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return [line.strip().lower() for line in f]

    @staticmethod
    def build_vocabulary(vocabulary):
        return set(word.lower() for word in vocabulary)

    @staticmethod
    def split_words(string):
        return [
            word.strip()
            for word in re.findall(r"[^\[\]\(\)（）]+", string)
            if word.strip() and not re.match(r"^[^\w]+$", word.strip())
        ]

    @staticmethod
    def remove_punctuation(input_string):
        return re.sub(r"^[^\w\s]+|[^\w\s]+$", "", input_string)

    def check_string_with_x(self, s):
        return bool(re.search(r"(?<![a-zA-Z0-9])[xX×&](?![a-zA-Z0-9])", s))

    def check_word(self, word):
        if word in self.vocabulary:
            return "常用词汇"
        simplified_word = convert(word, "zh-cn")
        if word in self.corpus or simplified_word in self.corpus:
            return "人名"
        if self.check_string_with_x(word):
            return "多人名"
        return None

    def get_title(self, title):
        for word in self.split_words(title):
            cleaned_word = self.remove_punctuation(word).lower()
            if self.check_word(cleaned_word) is None:
                return cleaned_word
        return None

    # 数字处理方法
    def _getNumberWithPrefix(self, s):
        pattern = r"vol\.(\d+)|chap\.(\d+)"
        match = re.search(pattern, s, re.IGNORECASE)
        if match:
            if match.group(1):
                return (float(match.group(1)), NumberType.VOLUME)
            elif match.group(2):
                return (float(match.group(2)), NumberType.CHAPTER)
        return (None, NumberType.NONE)

    @staticmethod
    def _roman_to_integer(s):
        roman_numerals = {"I": 1, "V": 5, "X": 10,
                          "L": 50, "C": 100, "D": 500, "M": 1000}
        total = 0
        prev = 0
        # 从右到左遍历字符
        for c in reversed(s.upper()):
            current = roman_numerals[c]
            total += current if current >= prev else -current
            prev = current
        return total

    def _getRomanNumber(self, s):
        # 罗马数字紧邻前后无英文字母
        match = re.search(r"(?<![A-Z])[IVXLCDM]+(?![A-Z])", s, re.IGNORECASE)
        if match:
            return (self._roman_to_integer(match.group(0)), NumberType.NORMAL)
        return (None, NumberType.NONE)

    def _normal_number(self, s):
        decimal_pattern = r"\d+\.\d"
        matches = re.findall(decimal_pattern, s)
        if not matches:
            matches = re.findall(r"\d+", s)
        if matches:
            return (float(matches[-1]), NumberType.NORMAL)
        return (None, NumberType.NONE)

    @staticmethod
    def formatString(s):
        return s.replace("-", ".").replace("_", ".")

    def getNumber(self, s):
        s = self.formatString(s)
        parsers = [self._getNumberWithPrefix,
                   self._getRomanNumber, self._normal_number]
        for parser in parsers:
            number, type = parser(s)
            if number is not None:
                return (number, type)
        return (None, NumberType.NONE)

    def parse(self, input_str):
        """
        一站式解析字符串，返回结构化结果
        """
        number, num_type = self.getNumber(input_str)
        title = self.get_title(input_str)

        return {
            'title': title,
            'episode': number,
            # 'num_type': num_type,
            'author': '',
            'year': '',
            'publisher': '',
            'excess': ''
        }
