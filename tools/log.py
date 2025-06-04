import sys
import os
import logging
from logging.handlers import RotatingFileHandler


def is_in_debug():
    """检测是否在调试模式下运行"""
    result = sys.gettrace()
    print("==============================")
    print(f"调试器: {result}")
    print("==============================")

    # 检查调试器钩子, 不为空则是启用了调试
    if result:
        return True
    else:
        return False


logger = logging.getLogger()
logger.setLevel(logging.INFO)
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
logger.addHandler(fh)

sh = logging.StreamHandler(sys.stdout)
sh.setFormatter(formatter)
# 感知调试器, 切换日志等级
sh.setLevel(logging.DEBUG if is_in_debug() else logging.INFO)
logger.addHandler(sh)
