from services.service_runner import run_service
import signal
import logging
import threading


def _signal_handler(signum, frame):
    """处理系统信号(SIGINT/SIGTERM)以优雅关闭服务"""
    logger = logging.getLogger(__name__)
    logger.info("收到信号 %s，正在关闭服务...", signum)
    # 由于 run_service 内部使用 threading.Event().wait() 阻塞，
    # 我们需要唤醒主线程以允许其处理关闭逻辑
    threading.Event().set()  # 唤醒主线程
    # 实际的清理工作由 service_runner.py 中的 wait_for_services 处理


def _setup_signal_handlers():
    """注册信号处理器"""
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)


def main():
    _setup_signal_handlers()
    run_service()


if __name__ == "__main__":
    main()
