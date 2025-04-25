import json
import os
import pickle
from tools.log import logger


class IndexedDataRead:
    def __init__(self, dataFilePath):
        self.file_path = dataFilePath
        self.id_offsets = self.load_index()

    def load_index(self):
        indexFilePath = f"{self.file_path}.index"
        if not os.path.exists(indexFilePath):
            return self.build_offsets_index(self.file_path)
        try:
            with open(indexFilePath, 'rb') as f:
                id_offsets = pickle.load(f)
                return id_offsets
        except FileNotFoundError as e:
            logger.error(f"索引文件未找到: {indexFilePath}")
            return {}

    def build_offsets_index(self):
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
                        if item["type"] == 1:
                            if item["id"] in id_offsets:
                                raise ValueError(item['id'])
                            id_offsets[item["id"]] = f.tell() - len(line)
                    except ValueError as e:
                        logger.warning(f"已存在 Subject ID: {e.args}")
                        continue
        except FileNotFoundError:
            logger.error(f"源数据文件未找到: {self.file_path}")
        # 保存索引缓存
        try:
            with open(indexFilePath, 'wb') as f:
                pickle.dump(id_offsets, f)
                logger.info(f"索引文件已保存至: {indexFilePath}")
        except Exception as e:
            logger.error(f"写入索引失败: {str(e)}")
            return {}
        return id_offsets

    def get_line_by_id(self, targetID: str) -> dict:
        """
        根据ID从数据文件中快速获取对应行内容
        """
        # 检查ID是否存在
        if targetID in self.id_offsets:
            offset = self.id_offsets[targetID]
        else:
            logger.warning(f"ID {targetID} 未在索引中找到")
            return {}

        # 根据偏移量定位并读取行
        try:
            with open(self.file_path, 'rb') as f:
                f.seek(offset)
                line = f.readline().decode('utf-8')
                return json.loads(line)  # 返回解析后的JSON对象
        except Exception as e:
            logger.error(f"读取行时发生错误: {str(e)}")
            return {}
