import threading
import signal
from tools.log import logger
from config.config import BANGUMI_KOMGA_SERVICE_TYPE
from core.refresh_metadata import refresh_metadata
from bangumi_archive.periodic_archive_checker import periodical_archive_check_service
from services.polling_service import PollManager
from services.sse_service import SseManager


def run_service():
    """启动 Bangumi Komga 服务"""
    service_type = BANGUMI_KOMGA_SERVICE_TYPE.lower()

    if service_type not in ("once", "poll", "sse"):
        logger.error("无效的服务类型: '%s'，请检查配置文件", BANGUMI_KOMGA_SERVICE_TYPE)
        return

    # ===========================================================
    # 首次全量刷新 (try/except 包裹，失败不崩溃)
    # ===========================================================
    try:
        refresh_metadata()
    except Exception:
        logger.exception("首次全量刷新失败，服务将继续运行")

    # ===========================================================
    # 按模式启动
    # ===========================================================
    if service_type == "once":
        _run_once_mode()
    elif service_type == "poll":
        _run_poll_mode()
    elif service_type == "sse":
        _run_sse_mode()


# ---------------------------------------------------------------------------
# once 模式: 单次全量刷新后退出 (适配 oflia / cron 等外部调度器)
# ---------------------------------------------------------------------------
def _run_once_mode():
    logger.info("once 模式: 等待 Archive 检查完成...")

    # 同步执行 Archive 检查 (不再用 daemon 线程，防止被提前杀死)
    archive_thread = periodical_archive_check_service()
    if archive_thread is not None:
        archive_thread.join(timeout=600)  # 最多等 10 分钟

    logger.info("once 模式执行完毕")


# ---------------------------------------------------------------------------
# poll 模式: 定时轮询 Komga API
# ---------------------------------------------------------------------------
def _run_poll_mode():
    stop_event = threading.Event()

    # 启动 Archive 定时检查
    archive_thread = periodical_archive_check_service()

    # 启动轮询管理器 (单层 daemon 线程)
    poll_mgr = PollManager(stop_event)
    poll_mgr.start()

    # 注册信号处理 (SIGINT/SIGTERM → set stop_event)
    _setup_stop_signals(stop_event)

    logger.info("poll 模式已启动，等待停止信号...")

    # 阻塞直到收到停止信号
    stop_event.wait()

    # 清理
    logger.info("正在停止服务...")
    poll_mgr.stop()
    if archive_thread is not None:
        archive_thread.join(timeout=10)
    logger.info("BangumiKomga 服务已停止")


# ---------------------------------------------------------------------------
# sse 模式: 订阅 Komga SSE 事件流
# ---------------------------------------------------------------------------
def _run_sse_mode():
    stop_event = threading.Event()

    # 启动 Archive 定时检查
    archive_thread = periodical_archive_check_service()

    # 启动 SSE 管理器 (单层 daemon 线程，内部管理 KomgaSseApi 生命周期)
    sse_mgr = SseManager(stop_event)
    sse_mgr.start()

    # 注册信号处理
    _setup_stop_signals(stop_event)

    logger.info("sse 模式已启动，等待停止信号...")

    # 阻塞直到收到停止信号
    stop_event.wait()

    # 清理
    logger.info("正在停止服务...")
    sse_mgr.stop()
    if archive_thread is not None:
        archive_thread.join(timeout=10)
    logger.info("BangumiKomga 服务已停止")


# ---------------------------------------------------------------------------
# 信号处理 (SIGINT / SIGTERM)
# ---------------------------------------------------------------------------
def _setup_stop_signals(stop_event):
    """在主线程注册 SIGINT 和 SIGTERM 的优雅停止处理器"""
    def _handler(signum, frame):
        sig_name = signal.Signals(signum).name
        logger.info("收到信号 %s，正在停止服务...", sig_name)
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(sig, _handler)
        except (ValueError, OSError):
            # 非主线程或受限环境（如某些 Docker 配置）中无法设置
            logger.debug("无法为 %s 注册信号处理器", sig.name)
