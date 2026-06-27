import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from tools.paths import LOG_DIR, LOG_FILENAME


def is_in_debug():
    """检测是否在调试模式下运行"""
    return bool(sys.gettrace())

def init_logger(debug_mode=None, log_dir=LOG_DIR, log_file_name=LOG_FILENAME):
    """初始化日志记录器"""
    if debug_mode is None:
        debug_mode = is_in_debug()
    logger = logging.getLogger()
    if logger.hasHandlers():
        return logger
    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(filename)-8s : %(lineno)s - %(message)s"
    )

    # 创建日志目录
    os.makedirs(log_dir, exist_ok=True)
    log_file_path = os.path.join(log_dir, log_file_name)

    fh = RotatingFileHandler(
        filename=log_file_path,
        maxBytes=10000000,
        backupCount=9,
        encoding="utf-8",
    )
    fh.setFormatter(formatter)
    fh.setLevel(logging.INFO)
    logger.addHandler(fh)

    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(formatter)
    # 感知调试器, 切换日志等级
    sh.setLevel(logging.DEBUG if debug_mode else logging.INFO)
    logger.addHandler(sh)

    return logger