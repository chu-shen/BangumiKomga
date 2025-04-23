from api.bangumiApi import BangumiDataSourceFactory
import api.komgaApi as komgaApi
from config.config import *
from tools.log import logger


class InitEnv:
    def __init__(self):
        BANGUMI_DATA_SOURCE_CONFIG = {
            'access_token': BANGUMI_ACCESS_TOKEN,
            'use_local_archive': USE_BANGUMI_ARCHIVE,
            'local_archive_folder': ARCHIVE_FILES_DIR
        }
        self.bgm = BangumiDataSourceFactory.create(BANGUMI_DATA_SOURCE_CONFIG)
        # Initialize the komga API
        self.komga = komgaApi.KomgaApi(
            KOMGA_BASE_URL, KOMGA_EMAIL, KOMGA_EMAIL_PASSWORD)
        self.all_series = []

        if KOMGA_LIBRARY_LIST and KOMGA_COLLECTION_LIST:
            logger.error(
                "Use only one of KOMGA_LIBRARY_LIST or KOMGA_COLLECTION_LIST")
        elif KOMGA_LIBRARY_LIST:
            for library in KOMGA_LIBRARY_LIST:
                self.all_series.extend(
                    self.komga.get_series_with_libaryid(library)['content'])
        elif KOMGA_COLLECTION_LIST:
            for collection in KOMGA_COLLECTION_LIST:
                self.all_series.extend(
                    self.komga.get_series_with_collection(collection)['content'])
        else:
            self.all_series = self.komga.get_all_series()['content']
