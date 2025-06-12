import re


class NumberType:
    VOLUME = "volume"
    CHAPTER = "chapter"
    NORMAL = "normal"
    NONE = "none"


def get_number_with_prefix(s):
    pattern = r"vol\.(\d+)|chap\.(\d+)"
    match = re.search(pattern, s, re.IGNORECASE)

    if match:
        if match.group(1):
            return (float(match.group(1)), NumberType.VOLUME)
        elif match.group(2):
            return (float(match.group(2)), NumberType.CHAPTER)
    return None, NumberType.NONE


def roman_to_integer(s):
    # FIXME: 遵循罗马数字规则
    # FIXME: 检查重复规则, V, L, D 不能重复
    # FIXME: 检查是否包含非法字符
    roman_numerals = {"I": 1, "V": 5, "X": 10,
                      "L": 50, "C": 100, "D": 500, "M": 1000}

    total = 0
    prev_value = 0

    for char in reversed(s):  # 从右到左遍历字符
        current_value = roman_numerals[char]

        if current_value < prev_value:
            total -= current_value  # 如果小于前一个值则减去
        else:
            total += current_value  # 否则加上

        prev_value = current_value

    return total


def get_roman_number(s):
    # 罗马数字紧邻前后无英文字母
    roman_pattern = r"(?<![A-Z])[IVXLCDM]+(?![A-Z])"
    match = re.search(roman_pattern, s, re.IGNORECASE)

    if match:
        roman_numeral = match.group(0)
        return roman_to_integer(roman_numeral.upper()), NumberType.NORMAL
    else:
        return None, NumberType.NONE


def normal(s):
    # Define the pattern to match decimal numbers in the format of "xx.xx"
    decimal_pattern = r"\d+\.\d+"
    # Use the `re.findall` function to search for all occurrences of the pattern in the input string
    match = re.findall(decimal_pattern, s)
    # If no decimal numbers are found, change the pattern to match integer numbers
    if not match:
        int_pattern = r"\d+"
        match = re.findall(int_pattern, s)

    if match:
        return float(match[-1]), NumberType.NORMAL
    return None, NumberType.NONE


def format_string(s):
    # e.g. 16-5
    return s.replace("-", ".").replace("_", ".")


def get_number(s):

    s = format_string(s)

    parsers = [get_number_with_prefix, get_roman_number, normal]

    for parser in parsers:
        number, type = parser(s)
        if number:
            return number, type

    return None, NumberType.NONE
