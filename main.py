from services.service_runner import run_service
from tools.log import logger
import os
import sqlite3


def main():
    run_service()


def prepare_procedure():
    """检查目录权限并提前创建必要目录"""
    try:
        # 准备日志目录
        os.makedirs('/logs', exist_ok=True)
        # 自动创建db文件
        with sqlite3.connect('recordsRefreshed.db') as conn:
            pass
    except Exception as e:
        logger.waring(f"环境准备出错: {e}, 请检查目录权限")
        return


if __name__ == "__main__":
    # 加入启动流程
    prepare_procedure()
    main()
