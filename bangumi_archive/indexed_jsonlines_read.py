import json
import os
import pickle
from tools.log import logger


class IndexedDataReader:
    def __init__(self, dataFilePath):
        self.file_path = dataFilePath
        self.id_offsets = self._load_index()

    def _load_index(self):
        indexFilePath = f"{self.file_path}.index"
        if not os.path.exists(indexFilePath):
            logger.warning(f"索引文件未找到: {indexFilePath}")
            return self.update_offsets_index()
        try:
            with open(indexFilePath, 'rb') as f:
                id_offsets = pickle.load(f)
                return id_offsets
        except pickle.UnpicklingError as e:
            logger.error(f"索引文件损坏: {indexFilePath}, 正在尝试重建......")
        except Exception as e:
            logger.error(f"索引文件读取出错: {indexFilePath}, {e}, 正在尝试重建......")
        return self.update_offsets_index()

    def update_offsets_index(self):
        if "relation" in self.file_path:
            return self._build_offsets_index(indexedFiled="subject_id")
        else:
            return self._build_offsets_index(indexedFiled="id")

    def _build_offsets_index(self, indexedFiled: str):
        """构建行偏移量索引"""
        id_offsets = {}
        indexFilePath = f"{self.file_path}.index"
        logger.info(f"开始构建索引文件: {self.file_path}")
        try:
            with open(self.file_path, 'rb') as f:
                while True:
                    try:
                        line = f.readline()
                        if not line:
                            break
                        item = json.loads(line.decode("utf-8"))
                        logger.debug(
                            f"构建行索引: {item}, ID: {item.get(indexedFiled)}")
                        if item[indexedFiled] in id_offsets:
                            id_offsets[item[indexedFiled]].append(
                                f.tell() - len(line))
                        else:
                            id_offsets[item[indexedFiled]
                                       ] = [f.tell() - len(line)]
                    except Exception as e:
                        logger.debug(f"构建索引文件时于 {line} 出错: {e}")
                        continue
        except FileNotFoundError:
            logger.error(f"源数据文件未找到: {self.file_path}")
        # 保存索引缓存
        try:
            with open(indexFilePath, 'wb') as f:
                pickle.dump(id_offsets, f)
                logger.info(f"索引文件已保存至: {indexFilePath}")
        except Exception as e:
            logger.error(f"写入索引失败: {e}")
            return {}
        return id_offsets

    def get_data_by_id(self, targetID: str, targetField: str) -> list:
        """
        根据ID从数据文件中快速获取对应行内容
        """
        try:
            targetID = int(targetID)
        except ValueError as e:
            logger.debug(f"无法将传入值视为 ID: {targetID}, {e}")
            return []

        # 检查ID是否存在
        if targetID not in self.id_offsets:
            logger.debug(f"未在索引中找到 ID: {targetID}")
            return []

        offsets = self.id_offsets[targetID]

        if not offsets:
            logger.debug(f"索引数据 {self.file_path} 中缺失 {str(targetID)} 数据")
            return []
        results = []
        # 根据偏移量定位并读取行
        try:
            with open(self.file_path, 'rb') as f:
                for offset in offsets:
                    f.seek(offset)
                    line = f.readline().decode('utf-8')
                    item = json.loads(line)
                    if item.get(targetField, 0) == targetID:
                        results.append(item)
                    else:
                        logger.debug(f"在 Archive 数据中缺失 {str(targetID)} 行")
            return results
        except Exception as e:
            logger.error(f"通过索引读取 Archive 时发生错误: {str(e)}")
            return results
