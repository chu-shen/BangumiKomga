from services.polling_service import poll_service
from services.sse_service import sse_service
import logging
logger = logging.getLogger(__name__)
from config.config import BANGUMI_KOMGA_SERVICE_TYPE
from core.refresh_metadata import refresh_metadata
from bangumi_archive.periodic_archive_checker import periodical_archive_check_service


def run_service():
    """
    启动 Bangumi Komga 服务
    """
    service_type = BANGUMI_KOMGA_SERVICE_TYPE.lower()

    # 启动Archive检查服务 (daemon 线程, 随主进程退出)
    periodical_archive_check_service()

    refresh_metadata()

    if service_type == "poll":
        run_poll_service()
    elif service_type == "sse":
        run_sse_service()
    elif service_type == "once":
        run_once_service()
    else:
        logger.error(
            "无效的服务类型: '%s'，请检查配置文件",
            BANGUMI_KOMGA_SERVICE_TYPE,
        )
        exit(1)


def run_poll_service():
    """运行轮询服务 — poll_service() 内部阻塞主线程."""
    poll_service()


def run_sse_service():
    """运行SSE服务 — sse_service() 内部阻塞主线程."""
    sse_service()


def run_once_service():
    """运行一次性服务"""
    pass
