from services.polling_service import poll_service
from services.sse_service import sse_service
from tools.log import logger
from config.config import BANGUMI_KOMGA_SERVICE_TYPE
from core.refresh_metadata import refresh_metadata
from bangumi_archive.periodic_archive_checker import periodical_archive_check_service


def run_service():
    """
    启动 Bangumi Komga 服务
    """
    service_type = BANGUMI_KOMGA_SERVICE_TYPE.lower()

    if service_type == "poll":
        poll_service()
        periodical_archive_check_service()
    elif service_type == "sse":
        sse_service()
        periodical_archive_check_service()
    elif service_type == "once":
        refresh_metadata()
    else:
        logger.error(
            "无效的服务类型: '%s'，请检查配置文件",
            BANGUMI_KOMGA_SERVICE_TYPE,
        )
        exit(1)
