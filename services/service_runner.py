from services.polling_service import poll_service
from services.sse_service import sse_service
from tools.log import logger
import threading
from config.config import BANGUMI_KOMGA_SERVICE_TYPE
from core.refresh_metadata import refresh_metadata
from bangumi_archive.periodic_archive_checker import periodical_archive_check_service


def run_service():
    """
    启动 Bangumi Komga 服务
    """
    service_type = BANGUMI_KOMGA_SERVICE_TYPE.lower()

    if service_type == "poll":
        refresh_metadata()
        refresh_service_thread = threading.Thread(target=poll_service, daemon=True)
        archive_check_thread= periodical_archive_check_service()
        refresh_service_thread.start()
    elif service_type == "sse":
        refresh_metadata()
        refresh_service_thread = threading.Thread(target=sse_service, daemon=True)
        archive_check_thread= periodical_archive_check_service()
        refresh_service_thread.start()
    elif service_type == "once":
        refresh_metadata()
    else:
        logger.error(
            "无效的服务类型: '%s'，请检查配置文件",
            BANGUMI_KOMGA_SERVICE_TYPE,
        )
        exit(1)
    try:
        refresh_service_thread.join()
        archive_check_thread.join()
    except KeyboardInterrupt:
        logger.warning("服务手动终止: 退出 BangumiKomga 服务")