import json
from datetime import datetime, timedelta
from typing import Optional
from tools.log import logger


class TimeCacheManager:
    """
    时间缓存管理类，处理更新时间记录的读写和转换
    """

    def read_time(file_path) -> str:
        """
        读取缓存中的更新时间字符串
        """
        try:
            with open(file_path, "r") as f:
                return json.load(f).get("last_updated", "1970-01-01T00:00:00Z")
        except FileNotFoundError:
            logger.warning(f"缓存文件 {file_path} 不存在，使用默认时间")
            return "1970-01-01T00:00:00Z"
        except json.JSONDecodeError as e:
            logger.warning(f"缓存文件 {file_path} 解析失败: {str(e)}")
            return "1970-01-01T00:00:00Z"

    def save_time(file_path, last_updated: str) -> None:
        """
        保存最新更新时间到缓存
        """
        with open(file_path, "w") as f:
            json.dump({"last_updated": last_updated}, f)

    def convert_to_timedelta(input_seconds: int) -> Optional[datetime]:
        """
        将分钟数转换为 datetime 对象
        """
        try:
            result = timedelta(minutes=input_seconds)
        except Exception as e:
            logger.warning(f"时间值 {input_seconds} 转换失败: {str(e)}")
            return None
        return result

    def convert_to_datetime(time_str: str) -> Optional[datetime]:
        """
        将 ISO 格式字符串转换为 datetime 对象
        """
        try:
            result = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
        except Exception as e:
            logger.warning(f"时间字符串 {time_str} 转换失败: {str(e)}")
            return None
        return result
