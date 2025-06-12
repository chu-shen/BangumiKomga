import threading
import time
from tools.log import logger
from config.config import ARCHIVE_CHECK_INTERVAL
from bangumi_archive.archive_autoupdater import check_archive


def periodical_archive_check_service():
    """守护线程执行定时检查"""
    def periodic_check():
        while True:
            interval = parse_interval(hours=12)
            try:
                check_archive()
                logger.info(f"将于 {interval} 秒后执行下次Archive更新检查")
            except Exception as e:
                logger.error(f"定时检查异常: {e}")

            time.sleep(interval)

    thread = threading.Thread(target=periodic_check, daemon=True)
    thread.start()
    return thread


def parse_interval(days: int = 0, hours: int = 0, minutes: int = 0, seconds: int = 0):
    """解析时间间隔配置"""

    result = days*24*60*60 + hours*60*60 + minutes*60 + seconds
    if result == 0:
        return 86400  # 默认每天检查
    else:
        return result
