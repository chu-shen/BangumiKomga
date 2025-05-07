import threading
import time
from tools.log import logger
from config.config import (
    USE_BANGUMI_KOMGA_SERVICE,
    SERVICE_POLL_INTERVAL,
    SERVICE_REFRESH_ALL_METADATA_INTERVAL,
)
from refreshMetadata import refresh_metadata, refresh_partial_metadata


class PollingCaller:
    def __init__(self):
        self.is_refreshing = False
        self.interval = SERVICE_POLL_INTERVAL
        # 多少次轮询后执行一次全量刷新
        self.refresh_all_metadata_interval = SERVICE_REFRESH_ALL_METADATA_INTERVAL
        self.refresh_counter = 0
        # 添加锁对象
        self.lock = threading.Lock()

    def _safe_refresh(self, refresh_func):
        """
        封装安全刷新操作
        """
        with self.lock:
            if self.is_refreshing:
                logger.warning("已有元数据刷新任务在运行")
                return False
            self.is_refreshing = True

        try:
            refresh_func()
            return True
        except Exception as e:
            logger.error(f"刷新失败: {str(e)}", exc_info=True)
            return False
        finally:
            with self.lock:
                self.is_refreshing = False

    def start_polling(self):
        """
        启动服务
        """

        def poll():
            while True:
                try:
                    if self.refresh_counter >= self.refresh_all_metadata_interval:
                        success = self._safe_refresh(refresh_metadata)
                        self.refresh_counter = 0
                    else:
                        success = self._safe_refresh(refresh_partial_metadata)

                    if not success:
                        retry_delay = min(2**self.interval, 60)
                        time.sleep(retry_delay)

                    self.refresh_counter += 1
                    # 等待一个预设时间间隔
                    time.sleep(self.interval)

                except Exception as e:
                    logger.error(f"轮询失败: {str(e)}", exc_info=True)
                    # 指数退避重试
                    retry_delay = min(2**self.interval, 60)
                    # 固定值重试
                    # retry_delay = self.interval
                    logger.warning(f"{retry_delay}秒后重试...")
                    time.sleep(retry_delay)
                    continue

        # 使用守护线程启动轮询
        threading.Thread(target=poll, daemon=True).start()


def main():
    PollingCaller().start_polling()

    # 防止服务主线程退出
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        logger.warning("服务手动终止: 退出 BangumiKomga 服务")


if __name__ == "__main__":
    if USE_BANGUMI_KOMGA_SERVICE:
        main()
    else:
        refresh_metadata()
