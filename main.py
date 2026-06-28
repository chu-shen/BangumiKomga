import signal
import sys
import logging

from tools.log import init_logger
from services.service_runner import run_service

logger = logging.getLogger(__name__)
_shutting_down = False


def _handle_signal(signum, frame):
    """SIGINT/SIGTERM: 第一次触发 KeyboardInterrupt, 第二次强制退出."""
    global _shutting_down
    if _shutting_down:
        logger.warning("收到第二次关闭信号, 强制退出")
        sys.exit(1)
    _shutting_down = True
    raise KeyboardInterrupt


def main():
    init_logger()
    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)
    run_service()


if __name__ == "__main__":
    main()
