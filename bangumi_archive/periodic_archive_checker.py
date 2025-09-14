import threading
import time
from tools.log import logger
from config.config import USE_BANGUMI_ARCHIVE, ARCHIVE_UPDATE_INTERVAL
from bangumi_archive.archive_autoupdater import check_archive


def periodical_archive_check_service():
    """守护线程执行定时检查"""
    if not USE_BANGUMI_ARCHIVE:
        logger.debug("Bangumi Archive 未启用，跳过 Archive 检查服务")
        return None

    if ARCHIVE_UPDATE_INTERVAL == 0:
        logger.debug("ARCHIVE_UPDATE_INTERVAL 为 0，跳过定时检查线程创建")
        return None

    def periodic_check():
        interval_seconds = parse_interval(hours=ARCHIVE_UPDATE_INTERVAL)

        while True:
            try:
                check_archive()
                logger.info(
                    f"下次更新检查将在 {ARCHIVE_UPDATE_INTERVAL} 小时后执行"
                )
            except Exception as e:
                logger.error(f"定时检查异常: {e}")

            time.sleep(interval_seconds)

    thread = threading.Thread(
        target=periodic_check, daemon=True, name="ArchiveUpdateChecker"
    )
    thread.start()
    return thread


def parse_interval(
    days: int = 0, hours: int = 0, minutes: int = 0, seconds: int = 0
) -> int:
    """解析时间间隔配置，返回总秒数"""
    if any(val < 0 for val in (days, hours, minutes, seconds)):
        raise ValueError("时间间隔参数不能为负数")

    return days * 86400 + hours * 3600 + minutes * 60 + seconds
