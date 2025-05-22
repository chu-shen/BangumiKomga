from api.bangumiApi import BangumiDataSourceFactory
import api.komgaApi as komgaApi
from config.config import *
from tools.log import logger
import threading


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

# 也许应该使用抽象类?


class BaseBangumiKomgService:
    def __init__(self):
        # 初始化共享资源
        self.komga = init_komga_client()
        self.bgm = init_bangumi_client()
        self.conn, self.cursor = init_sqlite3()
        self.lock = threading.Lock()
        self.log = logger
        # 共享配置参数
        self.use_thumbnail = USE_BANGUMI_THUMBNAIL
        self.failed_collection = CREATE_FAILED_COLLECTION

    def _get_series_record_db(self, series_id, success, message):
        with self.lock:
            self.cursor.execute()
            self.conn.commit()

    def _update_series_metadata(self, series, subject_id):
        # 获取元数据并验证
        metadata = self.bgm.get_subject_metadata(subject_id)
        if not metadata.isvalid:
            self._record_series_status(series["id"], False, "无效元数据")
            return False

        # 构建Komga元数据对象
        komga_data = processMetadata.setKomangaSeriesMetadata(
            metadata, series["name"], self.bgm)

        # 更新封面
        if self.use_thumbnail and not self.komga.has_thumbnail(series["id"]):
            thumbnail = self.bgm.get_subject_thumbnail(metadata)
            self.komga.update_thumbnail(series["id"], thumbnail)

        # 执行元数据更新
        success = self.komga.update_series_metadata(series["id"], komga_data)
        self._record_series_status(series["id"], success, message)
        return success

    def _handle_failed_collections(self, series_list):
        """统一处理失败收藏夹"""
        if not self.failed_collection:
            return
        failed_ids = [s["id"] for s in series_list if not s["success"]]
        if failed_ids:
            self.komga.replace_collection("FAILED_COLLECTION", failed_ids)


class PollingService(BaseBangumiKomgService):
    def __init__(self):
        super().__init__()
        self.interval = SERVICE_POLL_INTERVAL
        self.refresh_counter = 0
        self.full_refresh_interval = SERVICE_REFRESH_ALL_METADATA_INTERVAL
        self.lock = threading.Lock()

    def _run_partial_refresh(self):
        """增量刷新逻辑"""
        new_series = self._get_modified_series()
        if new_series:
            for series in new_series:
                self._process_series(series)

    def _run_full_refresh(self):
        """全量刷新逻辑"""
        all_series = self.komga.get_all_series()
        for series in all_series:
            self._process_series(series)

    def _process_series(self, series):
        """系列处理核心逻辑"""
        subject_id = self._get_subject_id(series)
        if not subject_id:
            self.log.error(f"无法获取{series['name']}的Bangumi ID")
            return
        self._update_series_metadata(series, subject_id)

    def _get_modified_series(self):
        """获取修改过的系列"""
        # 实现时间戳比较逻辑
        last_modified = TimeCacheManager.read_time(
            "komga_last_modified_time.json")
        return self.komga.get_series_modified_since(last_modified)

    def start(self):
        """启动轮询服务"""
        def polling_task():
            while True:
                try:
                    with self.lock:
                        if self.refresh_counter % self.full_refresh_interval == 0:
                            self._run_full_refresh()
                        else:
                            self._run_partial_refresh()
                        self.refresh_counter += 1
                except Exception as e:
                    self.log.error(f"轮询错误: {str(e)}", exc_info=True)
                time.sleep(self.interval)

        threading.Thread(target=polling_task, daemon=True).start()


class SseService(BaseKomgaService):
    def __init__(self):
        super().__init__()
        self.sse_client = KomgaSseClient(
            KOMGA_BASE_URL,
            KOMGA_EMAIL,
            KOMGA_EMAIL_PASSWORD,
            timeout=SSE_TIMEOUT
        )

    def _event_handler(self, event):
        """事件处理核心逻辑"""
        if event["type"] in ["SeriesAdded", "SeriesChanged"]:
            series_id = event["data"]["seriesId"]
            series = self.komga.get_series(series_id)
            self._process_series(series)

    def _process_series(self, series):
        """系列处理封装"""
        with self.lock:
            subject_id = self._get_subject_id(series)
            if subject_id:
                self._update_series_metadata(series, subject_id)

    def start(self):
        """启动SSE服务"""
        self.sse_client.on_event = self._event_handler
        self.sse_client.start()

    def stop(self):
        """优雅关闭"""
        self.sse_client.stop()
        super().stop()


class BangumiKomgaServiceFactory:
    def __init__(self):
        self.services = []
        self.config = load_config()

    def start_services(self):
        if self.config.USE_POLL:
            self._start_polling_service()
        if self.config.USE_SSE:
            self._start_sse_service()

        # 阻塞主线程
        try:
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            self.stop_services()

    def _start_polling_service(self):
        svc = PollingService()
        svc.start()
        self.services.append(svc)

    def _start_sse_service(self):
        svc = SseService()
        svc.start()
        self.services.append(svc)

    def stop_services(self):
        for svc in self.services:
            svc.stop()


# class PollingCaller:
#     def __init__(self):
#         self.is_refreshing = False
#         self.interval = SERVICE_POLL_INTERVAL
#         # 多少次轮询后执行一次全量刷新
#         self.refresh_all_metadata_interval = SERVICE_REFRESH_ALL_METADATA_INTERVAL
#         self.refresh_counter = 0
#         # 添加锁对象
#         self.lock = threading.Lock()

#     def _safe_refresh(self, refresh_func):
#         """
#         封装安全刷新操作
#         """
#         with self.lock:
#             if self.is_refreshing:
#                 logger.warning("已有元数据刷新任务在运行")
#                 return False
#             self.is_refreshing = True

#         try:
#             refresh_func()
#             return True
#         except Exception as e:
#             logger.error(f"刷新失败: {str(e)}", exc_info=True)
#             return False
#         finally:
#             with self.lock:
#                 self.is_refreshing = False

#     def start_polling(self):
#         """
#         启动服务
#         """

#         def poll():
#             while True:
#                 try:
#                     if self.refresh_counter >= self.refresh_all_metadata_interval:
#                         success = self._safe_refresh(refresh_metadata)
#                         self.refresh_counter = 0
#                     else:
#                         success = self._safe_refresh(refresh_partial_metadata)

#                     if not success:
#                         retry_delay = min(2**self.interval, 60)
#                         time.sleep(retry_delay)

#                     self.refresh_counter += 1
#                     # 等待一个预设时间间隔
#                     time.sleep(self.interval)

#                 except Exception as e:
#                     logger.error(f"轮询失败: {str(e)}", exc_info=True)
#                     # 指数退避重试
#                     retry_delay = min(2**self.interval, 60)
#                     # 固定值重试
#                     # retry_delay = self.interval
#                     logger.warning(f"{retry_delay}秒后重试...")
#                     time.sleep(retry_delay)
#                     continue

#         # 使用守护线程启动轮询
#         threading.Thread(target=poll, daemon=True).start()


# def main():
#     PollingCaller().start_polling()

#     # 防止服务主线程退出
#     try:
#         threading.Event().wait()
#     except KeyboardInterrupt:
#         logger.warning("服务手动终止: 退出 BangumiKomga 服务")
