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

    # 启动Archive检查服务
    archive_thread = periodical_archive_check_service()

    refresh_metadata()

    if service_type == "poll":
        run_poll_service(archive_thread)
    elif service_type == "sse":
        run_sse_service(archive_thread)
    elif service_type == "once":
        run_once_service()
    else:
        logger.error(
            "无效的服务类型: '%s'，请检查配置文件",
            BANGUMI_KOMGA_SERVICE_TYPE,
        )
        exit(1)


def run_poll_service(archive_thread):
    """运行轮询服务"""
    # 启动主服务线程
    service_thread = threading.Thread(
        target=poll_service, daemon=True, name="PollService"
    )
    service_thread.start()

    # 等待服务结束
    wait_for_services(service_thread, archive_thread)


def run_sse_service(archive_thread):
    """运行SSE服务"""
    # 启动主服务线程
    service_thread = threading.Thread(
        target=sse_service, daemon=True, name="SSEService"
    )
    service_thread.start()

    # 等待服务结束
    wait_for_services(service_thread, archive_thread)


def run_once_service():
    """运行一次性服务"""
    pass


def wait_for_services(service_thread, archive_thread=None):
    """
    等待服务线程结束

    Args:
        service_thread: 主服务线程
        archive_thread: Archive检查线程（可选）
    """
    try:
        # 等待主服务线程结束
        service_thread.join()
        # 如果有Archive线程，等待其结束
        if archive_thread is not None:
            archive_thread.join()
    except KeyboardInterrupt:
        logger.warning("服务手动终止: 退出 BangumiKomga 服务")
    finally:
        logger.info("BangumiKomga 服务已停止")
