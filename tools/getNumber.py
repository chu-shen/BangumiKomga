import re


class NumberType:
    VOLUME = "volume"
    CHAPTER = "chapter"
    NORMAL = "normal"
    NONE = "none"


def getNumberWithPrefix(s):
    pattern = r"vol\.(\d+)|chap\.(\d+)"
    match = re.search(pattern, s, re.IGNORECASE)

    if match:
        if match.group(1):
            return (float(match.group(1)), NumberType.VOLUME)
        elif match.group(2):
            return (float(match.group(2)), NumberType.CHAPTER)
    return None, NumberType.NONE


def roman_to_integer(s):
    roman_numerals = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}

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


def getRomanNumber(s):
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
    decimal_pattern = r"\d+\.\d"
    # Use the `re.findall` function to search for all occurrences of the pattern in the input string
    match = re.findall(decimal_pattern, s)
    # If no decimal numbers are found, change the pattern to match integer numbers
    if not match:
        int_pattern = r"\d+"
        match = re.findall(int_pattern, s)

    if match:
        return float(match[-1]), NumberType.NORMAL
    return None, NumberType.NONE


def formatString(s):
    # e.g. 16-5
    return s.replace("-", ".").replace("_", ".")


def getNumber(s):

    s = formatString(s)

    parsers = [getNumberWithPrefix, getRomanNumber, normal]

    for parser in parsers:
        number, type = parser(s)
        if number:
            return number, type

    return None, NumberType.NONE
