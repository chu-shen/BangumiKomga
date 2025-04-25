import re
import json
from tools.log import logger


def search_line_batch_optimized(
    file_path: str, subject_id: int, target_field: str, batch_size: int = 1000
):
    """
    从Archive文件中返回单个JSON对象
    """
    subject_id_bytes = str(subject_id).encode()
    try:
        with open(file_path, "rb") as f:
            while True:
                # 读取二进制数据块
                lines = []
                for _ in range(batch_size):
                    line = f.readline()
                    if not line:
                        break
                    lines.append(line)
                # 文件结束
                if not lines:
                    break

                # 二进制预过滤
                filtered_lines = []
                for line in lines:
                    if subject_id_bytes in line:
                        filtered_lines.append(line)

                # 解析过滤后的行
                for line in filtered_lines:
                    try:
                        item = json.loads(line.decode("utf-8"))
                        if item.get(target_field, 0) == subject_id:
                            return item
                    except json.JSONDecodeError:
                        pass
    except FileNotFoundError:
        logger.error(f"Archive文件未找到: {file_path}")
    except Exception as e:
        logger.error(f"读取Archive发生错误: {str(e)}")
    # 没有找到任何结果
    logger.error(f"Archive中不包含Subject_ID: {subject_id} 的元数据.")
    return None


def search_list_batch_optimized(
    file_path: str, subject_id: int, target_field: str, batch_size: int = 1000
):
    """
    从Archive文件中返回结果对象列表
    """
    results = []
    subject_id_bytes = str(subject_id).encode()
    try:
        with open(file_path, "rb") as f:
            while True:
                # 读取二进制数据块
                lines = []
                for _ in range(batch_size):
                    line = f.readline()
                    if not line:
                        break
                    lines.append(line)
                # 文件结束
                if not lines:
                    break

                # 二进制预过滤
                filtered_lines = []
                for line in lines:
                    if subject_id_bytes in line:
                        filtered_lines.append(line)

                # 解析过滤后的行
                for line in filtered_lines:
                    try:
                        item = json.loads(line.decode("utf-8"))
                        if item.get(target_field, 0) == subject_id:
                            results.append(item)
                    except json.JSONDecodeError:
                        pass
    except FileNotFoundError:
        logger.error(f"Archive文件未找到: {file_path}")
    except Exception as e:
        logger.error(f"读取Archive发生错误: {str(e)}")
    return results


def search_all_data_batch_optimized(file_path: str, query: str, batch_size: int = 1000):
    """
    从Archive文件中返回包含query且type==1的对象列表
    """
    results = []
    query_bytes = query.encode()
    try:
        with open(file_path, "rb") as f:
            while True:
                # 读取二进制数据块
                lines = []
                for _ in range(batch_size):
                    line = f.readline()
                    if not line:
                        break
                    lines.append(line)
                # 文件结束
                if not lines:
                    break

                # 二进制预过滤
                filtered_lines = []
                for line in lines:
                    if query_bytes in line:
                        filtered_lines.append(line)

                # 过滤出元数据类型 type == 1 的JSON对象
                for line in filtered_lines:
                    try:
                        item = json.loads(line.decode("utf-8"))
                        if item.get("type", 0) == 1:
                            results.append(item)
                    except json.JSONDecodeError:
                        pass
    except FileNotFoundError:
        logger.error(f"Archive文件未找到: {file_path}")
    except Exception as e:
        logger.error(f"读取Archive发生错误: {str(e)}")
    return results


def parse_infobox(infobox_str):
    """解析infobox模板字符串"""
    infobox = []
    lines = infobox_str.split("\n")
    current_key = None
    current_value = []

    for line in lines:
        line = line.strip()
        if line.startswith("{{") or line.startswith("}}"):
            continue
        if line.startswith("|"):
            if current_key:
                processed_value = process_value(current_key, current_value)
                infobox.append({"key": current_key, "value": processed_value})
            parts = line[1:].split("=", 1)
            if len(parts) == 2:
                current_key = parts[0].strip()
                current_value = parts[1].strip()
            else:
                current_key = None
        else:
            current_value += " " + line

    if current_key:
        processed_value = process_value(current_key, current_value)
        infobox.append({"key": current_key, "value": processed_value})
    return infobox


# 匹配中括号列表的正则表达式
RE_ARRAY_ENTRY = re.compile(r"\[(.*?)\]")


def process_value(key, value_str):
    """处理特殊字段（如别名、链接）"""
    if key == "别名":
        entries = []
        for entry in RE_ARRAY_ENTRY.findall(value_str):
            cleaned = entry.strip()  # 去除前后空格
            if cleaned:
                entries.append({"v": cleaned})
        return entries
    if key == "链接":
        entries = []
        for raw_entry in RE_ARRAY_ENTRY.findall(value_str):
            parts = raw_entry.split("|", 1)  # 按第一个|分割
            if len(parts) >= 2:
                key = parts[0].strip()
                value = parts[1].strip()
                entries.append({"k": key, "v": value})
        return entries
    return value_str.strip()
