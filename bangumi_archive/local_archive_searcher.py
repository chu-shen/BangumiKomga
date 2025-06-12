import re
import json
from tools.log import logger
from bangumi_archive.indexed_jsonlines_read import IndexedDataReader


def search_line(file_path: str, subject_id: int, target_field: str):
    """
    带健康检查和回退的单行数据搜索函数, 首选索引模式, 索引失效时自动切换批量模式
    """

    try:
        # 尝试索引模式
        result = _search_line_with_index(file_path, subject_id, target_field)
        if result:
            return result
        logger.debug(f"索引未命中: {subject_id}")

    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.debug(f"索引异常: {str(e)}，触发回退")
    except Exception as e:
        logger.debug(f"未知异常: {str(e)}")

    # 回退到批量查询模式
    return _search_line_batch_optimized(file_path, subject_id, target_field)


def _search_line_with_index(file_path: str, subject_id: int, target_field: str):
    """
    从Archive文件中返回单个JSON对象
    """
    try:
        indexed_data = IndexedDataReader(file_path)
        result = indexed_data.get_data_by_id(
            targetID=subject_id, targetField=target_field)
        if len(result) < 1:
            logger.debug(f"Archive 文件: {file_path} 中不包含 {subject_id} 相关数据")
            return None
        else:
            # FIXME: 返回搜索到的第一个对象是否合理？
            return result[0]
    except FileNotFoundError:
        logger.error(f"Archive 文件未找到: {file_path}")
    except Exception as e:
        logger.error(f"读取 Archive 发生错误: {str(e)}")
    return None


def _search_line_batch_optimized(
    file_path: str, subject_id: int, target_field: str, batch_size: int = 2000
):
    """
    从Archive文件中返回单个JSON对象
    """
    # 预编译匹配内容, 精确匹配字段
    # subject_id_bytes = str(subject_id).encode()
    target_field_pattern = re.compile(
        fr'"{target_field}"\s*:\s*{subject_id}'.encode()).search
    try:
        with open(file_path, "rb") as f:
            while True:
                # 读取二进制数据块
                lines = []
                for _ in range(batch_size):
                    line = f.readline()
                    if not line:
                        break
                    # 二进制预过滤
                    if target_field_pattern(line):
                        lines.append(line)

                # 文件结束
                if not lines:
                    break

                # 解析过滤后的行
                for line in lines:
                    try:
                        item = json.loads(line.decode("utf-8"))
                        if item.get(target_field, 0) == subject_id:
                            return item
                    except json.JSONDecodeError:
                        continue
    except FileNotFoundError:
        logger.error(f"Archive 文件未找到: {file_path}")
    except Exception as e:
        logger.error(f"读取 Archive 发生错误: {str(e)}")
    # 没有找到任何结果
    logger.debug(f"Archive 中不包含 Subject_ID: {subject_id} 的元数据.")
    return None


def search_list(
    file_path: str, subject_id: int, target_field: str
):
    """
    带健康检查和回退的多行数据搜索函数, 首选索引模式, 索引失效时自动切换批量模式
    """

    try:
        # 尝试索引模式
        result = _search_list_with_index(file_path, subject_id, target_field)
        if result:
            return result
        logger.debug(f"索引未命中: {subject_id}")

    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.debug(f"索引异常: {str(e)}，触发回退")
    except Exception as e:
        logger.debug(f"未知异常: {str(e)}")

    # 回退到批量查询模式
    return _search_list_batch_optimized(file_path, subject_id, target_field)


def _search_list_with_index(
    file_path: str, subject_id: int, target_field: str
):
    """
    从Archive文件中返回结果对象列表
    """
    try:
        indexed_data = IndexedDataReader(file_path)
        results = indexed_data.get_data_by_id(
            targetID=subject_id, targetField=target_field)
        if len(results) < 1:
            logger.debug(f"Archive 文件: {file_path} 中不包含 {subject_id} 相关数据")
            return []
        else:
            return results
    except FileNotFoundError:
        logger.error(f"Archive 文件未找到: {file_path}")
    except Exception as e:
        logger.error(f"读取 Archive 发生错误: {str(e)}")
    return []


def _search_list_batch_optimized(
    file_path: str, subject_id: int, target_field: str, batch_size: int = 2000
):
    """
    从Archive文件中返回结果对象列表
    """
    results = []
    # subject_id_bytes = str(subject_id).encode()
    # 构建目标字段的正则表达式模式
    # 使用 search 而非 match，允许匹配任意位置
    target_pattern = re.compile(
        fr'"{target_field}"\s*:\s*{subject_id}(?=\s*[,\}}])'.encode()).search
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
                    if target_pattern(line):
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
        logger.error(f"Archive 文件未找到: {file_path}")
    except Exception as e:
        logger.error(f"读取 Archive 发生错误: {str(e)}")
    # 搜索到多少就返回多少
    return results


def search_all_data(file_path: str, query: str):
    """
    带模式回退的全量数据搜索函数, 首选索引模式, 索引失效时自动切换批量模式
    """
    try:
        # 尝试索引模式
        result = _search_all_data_with_index(file_path, query)
        if result:
            return result
        logger.debug(f"索引全量搜索未命中: {query}")
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.debug(f"索引异常: {str(e)}，触发回退")
    except Exception as e:
        logger.debug(f"未知异常: {str(e)}")
    # 回退到批量查询模式
    return _search_all_data_batch_optimized(file_path, query)


def _search_all_data_with_index(file_path: str, query: str):
    """
    使用索引读取器返回所有type==1的对象列表
    """
    try:
        indexed_data = IndexedDataReader(file_path)
        results = []
        # 遍历所有索引项进行过滤
        for item in indexed_data:
            try:
                # 先检查类型匹配
                if item.get("type", 0) != 1:
                    continue
                # 再检查查询字符串匹配（模糊匹配）
                if query.encode() in json.dumps(item).encode():
                    results.append(item)
            except Exception as e:
                logger.debug(f"索引项过滤异常: {str(e)}")
                continue
        if not results:
            logger.debug(f"索引全量搜索无结果: {query}")
        return results
    except FileNotFoundError:
        logger.error(f"Archive 文件未找到: {file_path}")
    except Exception as e:
        logger.error(f"读取 Archive 发生错误: {str(e)}")
    # 搜索到多少就返回多少
    return results


def _search_all_data_batch_optimized(file_path: str, query: str, batch_size: int = 1000):
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
        logger.error(f"Archive 文件未找到: {file_path}")
    except Exception as e:
        logger.error(f"读取 Archive 发生错误: {str(e)}")
    # 搜索到多少就返回多少
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
                processed_value = _process_value(
                    current_key, " ".join(current_value))
                infobox.append({"key": current_key, "value": processed_value})
            parts = line[1:].split("=", 1)
            if len(parts) == 2:
                current_key = parts[0].strip()
                current_value = [parts[1].strip()]
            else:
                current_key = None
        else:
            current_value.append(line)

    if current_key:
        processed_value = _process_value(current_key, " ".join(current_value))
        infobox.append({"key": current_key, "value": processed_value})
    return infobox


# 匹配中括号列表的正则表达式
RE_ARRAY_ENTRY = re.compile(r"\[(.*?)\]")


def _process_value(key, value_str):
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
                k, v = parts[0].strip(), parts[1].strip()
                entries.append({"k": k, "v": v})
        return entries
    return value_str.strip()
