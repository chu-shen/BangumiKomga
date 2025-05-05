from api.bangumiApi import BangumiDataSourceFactory
import api.komgaApi as komgaApi
from config.config import *


class InitEnv:
    def __init__(self):
        BANGUMI_DATA_SOURCE_CONFIG = {
            "access_token": BANGUMI_ACCESS_TOKEN,
            "use_local_archive": USE_BANGUMI_ARCHIVE,
            "local_archive_folder": ARCHIVE_FILES_DIR,
        }
        self.bgm = BangumiDataSourceFactory.create(BANGUMI_DATA_SOURCE_CONFIG)
        # Initialize the komga API
        self.komga = komgaApi.KomgaApi(
            KOMGA_BASE_URL, KOMGA_EMAIL, KOMGA_EMAIL_PASSWORD
        )