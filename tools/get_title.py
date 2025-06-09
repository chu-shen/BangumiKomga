import re
from zhconv import convert


def read_corpus(file_path):
    """
    Read the contents of a text file and return a list of lowercase strings (lines)
    """
    with open(file_path, "r", encoding="utf-8") as f:
        # Read each line from the file, strip leading and trailing whitespaces, and convert to lowercase
        return [line.strip().lower() for line in f]


def build_vocabulary(vocabulary):
    """
    Build a set of lowercase words from a list of words
    """
    # Convert each word in the list to lowercase and store in a set
    return set(word.lower() for word in vocabulary)


def split_words(string):
    """
    Split a string into words using regular expression

    e.g. [ツガノガク] [涼宮春日的憂鬱] [台灣角川] [1-20完] -> ['ツガノガク', '涼宮春日的憂鬱', '台灣角川', '1-20完']
    """
    # Use a regular expression to find all non-empty substrings between square brackets and parentheses
    return [
        word.strip()
        for word in re.findall(r"[^\[\]\(\)（）]+", string)
        if word.strip() and not re.match(r"^[^\w]+$", word.strip())
    ]


def remove_punctuation(input_string):
    """
    Remove punctuation from a string
    """
    # Use a regular expression to remove non-word and non-whitespace characters
    return re.sub(r"^[^\w\s]+|[^\w\s]+$", "", input_string)


def check_string_with_x(s):
    """
    e.g. [大暮維人×西尾維新]
    """
    # 匹配字符串中的所有字母x（包括大小写），且前后不为字母数字
    pattern = r"(?<![a-zA-Z0-9])x(?![a-zA-Z0-9])"
    # 使用re库的search函数匹配字符串，如果有匹配到的字符，返回True；否则返回False
    if bool(re.search(pattern, s)):
        return True
    elif bool(re.search(r"×", s)):
        return True
    # 待验证：是否多数漫画包含&
    elif bool(re.search(r"\&", s)):
        return True
    else:
        return False


def check_word(word, corpus, vocabulary):
    """
    Check if a word is in the corpus or vocabulary, and return its type if it is
    """
    # Check if the word is in the vocabulary
    if word in vocabulary:
        return "常用词汇"
    # Check if the word is in the corpus or if its simplified Chinese equivalent is in the corpus
    elif word in corpus or convert(word, "zh-cn") in corpus:
        return "人名"
    elif check_string_with_x(word):
        return "多人名"
    # Return None if the word is not in either the corpus or vocabulary
    else:
        return None


class ParseTitle:
    def __init__(self):
        self.corpus = []
        self.vocabulary = set()
        self.load_resources()

    def load_resources(self):
        # Load the corpus and vocabulary
        self.corpus = read_corpus(
            "corpus/Japanese_Names_Corpus（18W）.txt"
        ) + read_corpus("corpus/bangumi_person.txt")
        self.vocabulary = build_vocabulary(
            ["comic", "comics", "artbook", "artbooks", "汉化", "全彩版", "青文"]
        )

    def get_title(self, title):
        """
        Get the first word from a title that is not in the corpus or vocabulary
        """
        # Iterate through the words in the title
        for word in split_words(title):
            # convert to lowercase
            word = remove_punctuation(word).lower()
            # Check the word against the corpus and vocabulary
            result = check_word(word, self.corpus, self.vocabulary)
            # Return the word if it is not in the corpus or vocabulary
            if result is None:
                return word
