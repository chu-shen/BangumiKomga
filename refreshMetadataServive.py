# main.py
from refreshMetadata import refresh_metadata, refresh_partial_metadata
from config.config import (
    USE_BANGUMI_KOMGA_SERVICE,
    SERVICE_POLL_INTERVAL,
    SERVICE_REFRESH_ALL_METADATA_INTERVAL,
)
from tools.log import logger
import time
import threading
import config  # 假设已创建config.py保存配置
from BangumiKomgService import PollingService, SseService  # 假设已创建services.py存放服务类
from tools.log import logger  # 假设已创建日志系统


def start_services():
    services = None
    if config.USE_BANGUMI_KOMGA_SERVICE_POLL:
        services = PollingService()
    if config.USE_BANGUMI_KOMGA_SERVICE_SSE:
        services = SseService()
    if services:
        # 改为仅启动一种服务
        services.start()
    else:
        logger.error(f"无法启动服务, 未指定服务配置项")
        return
    try:
        while True:
            threading.Event().wait()
    except KeyboardInterrupt:
        logger.warning("服务手动终止: 退出 BangumiKomga 服务")
        for svc in services:
            svc.stop()


if __name__ == "__main__":
    if USE_BANGUMI_KOMGA_SERVICE_POLL or USE_BANGUMI_KOMGA_SERVICE_SSE:
        start_services()
    else:
        refresh_metadata()
