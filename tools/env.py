from api.bangumi_api import BangumiDataSourceFactory
import api.komga_api as komga_api
from config.config import *
import os
import sqlite3
from tools.log import logger


class InitEnv:
    def __init__(self):
        # 启动准备
        self.prepare_procedure()
        # 读取配置
        BANGUMI_DATA_SOURCE_CONFIG = {
            "access_token": BANGUMI_ACCESS_TOKEN,
            "use_local_archive": USE_BANGUMI_ARCHIVE,
            "local_archive_folder": ARCHIVE_FILES_DIR,
        }
        # 初始化 bangumi API
        self.bgm = BangumiDataSourceFactory.create(BANGUMI_DATA_SOURCE_CONFIG)
        # 初始化 komga API
        self.komga = komga_api.KomgaApi(
            KOMGA_BASE_URL, KOMGA_EMAIL, KOMGA_EMAIL_PASSWORD
        )

    def prepare_procedure():
        """检查目录权限并提前创建必要目录"""
        try:
            # 准备日志目录
            os.makedirs("./logs", exist_ok=True)
            # 自动创建db文件
            with sqlite3.connect("recordsRefreshed.db") as conn:
                pass
        except Exception as e:
            logger.warning(f"环境准备出错: {e}, 请检查目录权限")
            return
