from services.polling_service import poll_service
from services.sse_service import sse_service
import logging
logger = logging.getLogger(__name__)
from config.config import BANGUMI_KOMGA_SERVICE_TYPE
from core.refresh_metadata import refresh_metadata
from bangumi_archive.periodic_archive_checker import start_archive_service


def run_service():
    """启动 Bangumi Komga 服务.

    Archive 服务在所有模式下均先启动并等待就绪, 再执行 refresh_metadata:
      once: wait_ready → refresh_metadata → 退出
      poll: wait_ready → refresh_metadata → 阻塞轮询
      sse:  wait_ready → refresh_metadata → 阻塞 SSE
    所有模式通过 try/finally 保证 archive_service.stop() 在退出时执行.
    """
    service_type = BANGUMI_KOMGA_SERVICE_TYPE.lower()

    # 启动 Archive 服务 (后台下载 + 定时更新)
    archive_service = start_archive_service()

    if archive_service is not None:
        logger.info("等待 Archive 数据准备完成...")
        ready = archive_service.wait_ready(timeout=600)
        if not ready:
            logger.warning("Archive 数据未在规定时间内准备就绪")
        else:
            logger.info("Archive 数据已就绪")

    refresh_metadata()

    try:
        if service_type == "poll":
            poll_service()           # 内部阻塞主线程, 自行处理 Ctrl+C/stop
        elif service_type == "sse":
            sse_service()            # 内部阻塞主线程, 自行处理 Ctrl+C/stop
        elif service_type == "once":
            pass  # archive 已就绪, refresh_metadata 已完成
        else:
            logger.error(
                "无效的服务类型: '%s'，请检查配置文件",
                BANGUMI_KOMGA_SERVICE_TYPE,
            )
            exit(1)
    finally:
        if archive_service is not None:
            archive_service.stop()
