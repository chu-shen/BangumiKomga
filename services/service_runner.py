from services.polling_service import poll_service
from services.sse_service import sse_service
from tools.log import logger
from config.config import BANGUMI_KOMGA_SERVICE_TYPE
from core.refresh_metadata import refresh_metadata


def run_service():
    """
    启动 Bangumi Komga 服务
    """
    service_type = BANGUMI_KOMGA_SERVICE_TYPE.lower()

    if service_type == "poll":
        refresh_metadata()
        poll_service()
    elif service_type == "sse":
        refresh_metadata()
        sse_service()
    elif service_type == "once":
        refresh_metadata()
    else:
        logger.error(
            "无效的服务类型: '%s'，请检查配置文件",
            BANGUMI_KOMGA_SERVICE_TYPE,
        )
        exit(1)
