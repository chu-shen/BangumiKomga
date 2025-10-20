import json
import os
import pickle
import re
import mmap
from threading import Lock
from typing import Dict, List, Union
from tools.log import logger


class IndexedDataReader:
    _instance: Dict[str, 'IndexedDataReader'] = {}  # file_path -> 实例
    _instance_lock = Lock()

    def __new__(cls, file_path: str):
        """
        用 __new__ 来实现单例缓存, 相同 file_path 返回同一个实例
        """
        with cls._instance_lock:
            if file_path in cls._instance:
                reader = cls._instance[file_path]
                # 检查数据文件是否被修改，若修改则重建索引
                if os.path.exists(file_path) and os.path.exists(reader.index_path):
                    data_mtime = os.path.getmtime(file_path)
                    index_mtime = os.path.getmtime(reader.index_path)
                    if data_mtime > index_mtime:
                        logger.warning(
                            f"Archive 数据 {file_path} 已被修改，开始重建索引...")
                        reader.index = reader._build_index()
                        logger.info(f"索引重建完成: {file_path}")
                # 直接返回缓存的实例
                return reader

            # 没有缓存，创建新实例
            instance = super().__new__(cls)
            cls._instance[file_path] = instance
            logger.debug(f"添加 IndexedDataReader 实例: {file_path}")
            return instance

    def __init__(self, dataFilePath):
        # 防止重复初始化
        if hasattr(self, 'file_path'):
            return
        self.file_path = dataFilePath
        self.index_path = f"{dataFilePath}.index"
        self.index = self._load_index()

    def _load_index(self):
        """自动判断索引过期并重建索引的索引加载器"""
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"未找到 Archive 数据: {self.file_path}")
        if not os.path.exists(self.index_path):
            logger.error(f"未找到索引文件: {self.index_path}")
            return self._build_index()
        if os.path.getsize(self.index_path) == 0:
            logger.error(f"索引文件为空: {self.index_path}")
            return self._build_index()

        data_mtime = os.path.getmtime(self.file_path)
        index_mtime = os.path.getmtime(self.index_path)

        try:
            with open(self.index_path, 'rb') as f:
                index = pickle.load(f)
            # 检查文件修改时间
            if index_mtime >= data_mtime:
                logger.info(f"索引加载成功: {self.index_path}")
                return index
            else:
                logger.warning(f"索引版本或文件时间不匹配，将重建: {self.index_path}")
        except (pickle.UnpicklingError, EOFError) as e:
            logger.error(f"索引文件损坏: {self.index_path}, 正在尝试重建......")
        except Exception as e:
            logger.error(f"索引读取失败: {self.index_path}, {e}")

        # 重建索引
        return self._build_index()

    def _build_index(self) -> Dict[str, Dict[Union[int, str], List[int]]]:
        """
        构建索引，仅索引以下字段:
        - 基础字段: id, type, subject_id, name, name_cn
        - infobox 中解析出的: name_cn_infobox, aliases_infobox
        """
        index: Dict[str, Dict[Union[int, str], List[int]]] = {
            "id": {},
            "type": {},
            "subject_id": {},
            "name": {},
            "name_cn": {},
            "name_cn_infobox": {},
            "aliases_infobox": {}
        }
        line_number = 0
        offset = 0

        def _add_to_index(field: str, value: Union[int, str], offset: int):
            if field not in index:
                return
            if value not in index[field]:
                index[field][value] = []
            index[field][value].append(offset)

        def _process_value(key: str, value_str: str) -> str:
            """处理字段值，去除多余空格等"""
            if not value_str:
                return ""
            return value_str.strip()
        # 解析 infobox 的工具函数（保持在本模块）

        def parse_infobox(infobox_str: str) -> Dict[str, List[str]]:
            """解析 infobox 字符串，返回 {'name_cn': [...], 'aliases': [...] }"""
            result = {"name_cn": [], "aliases": []}
            if not infobox_str or not isinstance(infobox_str, str):
                return result

            lines = infobox_str.split("\n")
            current_key = None
            current_value = []

            for line in lines:
                line = line.strip()
                if line.startswith("{{") or line.startswith("}}"):
                    continue
                if line.startswith("|"):
                    if current_key:
                        processed = _process_value(
                            current_key, " ".join(current_value))
                        if current_key == "中文名" and processed:
                            result["name_cn"].append(processed)
                        elif current_key == "别名":
                            # 提取 [xxx] 中的内容
                            entries = re.findall(r"\[(.*?)\]", processed)
                            result["aliases"].extend(
                                [e.strip() for e in entries if e.strip()])
                    parts = line[1:].split("=", 1)
                    if len(parts) == 2:
                        current_key = parts[0].strip()
                        current_value = [parts[1].strip()]
                    else:
                        current_key = None
                else:
                    current_value.append(line)

            if current_key:
                processed = _process_value(
                    current_key, " ".join(current_value))
                if current_key == "中文名" and processed:
                    result["name_cn"].append(processed)
                elif current_key == "别名":
                    entries = re.findall(r"\[(.*?)\]", processed)
                    result["aliases"].extend([e.strip()
                                             for e in entries if e.strip()])

            return result

        logger.info(f"开始构建索引: {self.file_path}")
        try:
            with open(self.file_path, 'rb') as f:
                with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                    while True:
                        line = mm.readline()
                        if not line:
                            break
                        line_number += 1
                        try:
                            item = json.loads(line.decode('utf-8'))
                            item_offset = offset

                            # 基础字段索引
                            for key in ["id", "type", "subject_id", "name", "name_cn"]:
                                val = item.get(key)
                                if val is not None:
                                    _add_to_index(key, val, item_offset)

                            # 解析 infobox
                            infobox_str = item.get("infobox", "")
                            infobox_parsed = parse_infobox(infobox_str)

                            # 索引 infobox 中的中文名和别名
                            for cn in infobox_parsed["name_cn"]:
                                _add_to_index("name_cn_infobox",
                                              cn, item_offset)
                            for alias in infobox_parsed["aliases"]:
                                _add_to_index("aliases_infobox",
                                              alias, item_offset)

                        except Exception as e:
                            logger.warning(f"解析第 {line_number} 行失败: {e}")
                            continue

                        offset += len(line)

        except Exception as e:
            logger.error(f"构建索引时出错: {e}")
            raise

        # 保存索引
        try:
            with open(self.index_path, 'wb') as f:
                pickle.dump(index, f, protocol=pickle.HIGHEST_PROTOCOL)
            logger.info(
                f"索引构建完成，共 {line_number} 行，已保存至: {self.index_path}，大小: {os.path.getsize(self.index_path) / 1024 / 1024:.1f} MB")
        except Exception as e:
            logger.error(f"保存索引失败: {e}")
            raise

        return index

    def _get_lines_by_offsets(self, offsets: List[int]) -> List[dict]:
        """根据偏移量列表，从 mmap 中读取并解析 JSON 行"""
        results = []
        try:
            with open(self.file_path, 'rb') as f:
                with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                    for offset in offsets:
                        mm.seek(offset)
                        line = mm.readline().decode('utf-8', errors='ignore')
                        try:
                            item = json.loads(line)
                            results.append(item)
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            logger.error(f"通过偏移量读取 Archive 数据失败: {e}")
        return results

    def get_data_by_query(self, *args, **query: Union[int, str]) -> List[dict]:
        """
        支持多字段联合查询：
        get_data_by_query(id=190714, type=1)
        get_data_by_query(name_cn="早乙女选手躲躲藏藏", subject_id=190714)

        返回同时满足所有条件的行
        """
        if args:
            # 全文模糊搜索
            if len(args) > 1:
                raise TypeError("全文搜索只接受一个字符串参数")
            if not isinstance(args[0], str):
                raise TypeError("全文搜索参数必须是字符串")

            search_term = args[0].lower()
            matching_offsets = set()

            # 可查询的字段
            searchable_fields = [
                "id", "type", "subject_id", "name", "name_cn",
                "name_cn_infobox", "aliases_infobox"
            ]

            for field in searchable_fields:
                if field not in self.index:
                    continue
                field_index = self.index[field]
                for key, offsets in field_index.items():
                    # 将键转为字符串并转小写进行子串匹配
                    key_str = str(key).lower()
                    if search_term in key_str:
                        matching_offsets.update(offsets)

            return self._get_lines_by_offsets(list(matching_offsets))

        if not query:
            return []

        # 获取所有字段的偏移量集合
        offset_sets = []
        for field, value in query.items():
            if field not in self.index:
                logger.debug(f"查询字段不在索引中: {field}")
                return []  # 任意字段不存在，直接返回空
            if value not in self.index[field]:
                return []  # 值不存在，直接返回空
            offset_sets.append(set(self.index[field][value]))

        if not offset_sets:
            return []

        # 求交集
        common_offsets = offset_sets[0]
        for offset_set in offset_sets[1:]:
            common_offsets &= offset_set

        return self._get_lines_by_offsets(list(common_offsets))
