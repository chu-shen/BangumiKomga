import re
import json
from tools.log import logger


# 匹配方括号列表的正则表达式
RE_ARRAY_ENTRY = re.compile(r'\[(.*?)\]')


# TODO: 也许分块读入然后在内存里遍历?
def iterate_archive_lines(file_path: str):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_number, line in enumerate(f, 1):
                if not line:
                    continue  # 跳过空行
                try:
                    yield json.loads(line.strip())
                except json.JSONDecodeError as e:
                    logger.warning(f"Archive文件第 {line_number} 行解析失败: {str(e)}")
                    continue
    except FileNotFoundError:
        logger.error(f"Archive文件未找到: {file_path}")
    except Exception as e:
        logger.error(f"读取Archive发生错误: {str(e)}")


def parse_infobox(infobox_str):
    """解析infobox模板字符串"""
    infobox = []
    lines = infobox_str.split('\n')
    current_key = None
    current_value = []

    for line in lines:
        line = line.strip()
        if line.startswith('{{') or line.startswith('}}'):
            continue
        if line.startswith('|'):
            if current_key:
                processed_value = process_value(current_key, current_value)
                infobox.append({'key': current_key, 'value': processed_value})
            parts = line[1:].split('=', 1)
            if len(parts) == 2:
                current_key = parts[0].strip()
                current_value = parts[1].strip()
            else:
                current_key = None
        else:
            current_value += ' ' + line

    if current_key:
        processed_value = process_value(current_key, current_value)
        infobox.append({'key': current_key, 'value': processed_value})
    return infobox


def process_value(key, value_str):
    """处理特殊字段（如别名、链接）"""
    if key == '别名':
        entries = []
        for entry in RE_ARRAY_ENTRY.findall(value_str):
            cleaned = entry.strip()  # 去除前后空格
            if cleaned:
                entries.append({"v": cleaned})
        return entries
    if key == '链接':
        entries = []
        for raw_entry in RE_ARRAY_ENTRY.findall(value_str):
            parts = raw_entry.split('|', 1)  # 按第一个|分割
            if len(parts) >= 2:
                key = parts[0].strip()
                value = parts[1].strip()
                entries.append({"k": key, "v": value})
        return entries
    return value_str.strip()
