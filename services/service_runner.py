from services.polling_service import poll_service
from services.sse_service import sse_service
import logging
logger = logging.getLogger(__name__)
import threading
from config.config import BANGUMI_KOMGA_SERVICE_TYPE
from core.refresh_metadata import refresh_metadata
from bangumi_archive.periodic_archive_checker import start_archive_service


def run_service():
    """启动 Bangumi Komga 服务."""
    service_type = BANGUMI_KOMGA_SERVICE_TYPE.lower()

    # 启动 Archive 服务 (后台下载 + 定时更新)
    archive_service = start_archive_service()

    refresh_metadata()

    try:
        if service_type == "poll":
            run_poll_service()
        elif service_type == "sse":
            run_sse_service()
        elif service_type == "once":
            run_once_service(archive_service)
        else:
            logger.error(
                "无效的服务类型: '%s'，请检查配置文件",
                BANGUMI_KOMGA_SERVICE_TYPE,
            )
            exit(1)
    finally:
        if archive_service is not None:
            archive_service.stop()


def run_poll_service():
    """运行轮询服务."""
    service_thread = threading.Thread(
        target=poll_service, daemon=True, name="PollService"
    )
    service_thread.start()
    _wait_service(service_thread)


def run_sse_service():
    """运行SSE服务."""
    service_thread = threading.Thread(
        target=sse_service, daemon=True, name="SSEService"
    )
    service_thread.start()
    _wait_service(service_thread)


def run_once_service(archive_service):
    """运行一次性服务 — 等 archive 就绪后退出."""
    if archive_service is not None:
        logger.info("等待 Archive 数据准备完成...")
        ready = archive_service.wait_ready(timeout=600)
        if not ready:
            logger.warning("Archive 数据未在规定时间内准备就绪")
        else:
            logger.info("Archive 数据已就绪")


def _wait_service(service_thread):
    try:
        service_thread.join()
    except KeyboardInterrupt:
        logger.warning("服务手动终止: 退出 BangumiKomga 服务")
