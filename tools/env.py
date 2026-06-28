from api.bangumi_api import BangumiDataSourceFactory
import api.komga_api as komga_api
from config.config import *
import os
import logging
from tools.paths import PROJECT_ROOT, ensure_runtime_layout
logger = logging.getLogger(__name__)
from config.configuration_generator import start_config_generate


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

    def prepare_procedure(self):
        """检查目录权限并提前创建必要目录"""
        # 关键路径：失败则直接崩溃，避免后续静默出错
        ensure_runtime_layout()

        config_file = os.path.join(PROJECT_ROOT, "config", "config.py")
        generated_config_file = os.path.join(
            PROJECT_ROOT, "config", "config.generated.py")
        try:
            if not os.path.exists(config_file) or os.path.getsize(config_file) == 0:
                    start_config_generate()
                    if os.path.exists(generated_config_file):
                        os.rename(generated_config_file, config_file)

        except PermissionError as e:
            logger.warning(f"权限不足，无法创建目录/文件: {e}")
        except OSError as e:
            logger.warning(f"文件系统操作失败: {e}")
        except Exception as e:
            logger.warning(f"环境准备出错: {e}")
            return
