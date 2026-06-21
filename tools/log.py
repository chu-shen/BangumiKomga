import sys
import logging
from logging.handlers import RotatingFileHandler


# 配置根 logger
_logger = logging.getLogger()
_logger.setLevel(logging.INFO)


def is_in_debug():
    """检测是否在调试模式下运行"""
    result = sys.gettrace()
    _logger.debug(f"调试器检测结果: {result}")
    return bool(result)


# pytest: module 集合时 "pytest" 已在 sys.modules；unittest: test_ 前缀文件在此进程arg中
_in_test = "pytest" in sys.modules

if not _in_test:
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(filename)-8s : %(lineno)s - %(message)s"
    )

    fh = RotatingFileHandler(
        filename="logs/refreshMetadata.log",
        maxBytes=10000000,
        backupCount=9,
        encoding="utf-8",
    )
    fh.setFormatter(formatter)
    fh.setLevel(logging.INFO)
    _logger.addHandler(fh)

    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(formatter)
    sh.setLevel(logging.DEBUG if is_in_debug() else logging.INFO)
    _logger.addHandler(sh)

# 向后兼容：仍然暴露 logger
logger = _logger
