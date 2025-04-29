import threading
import time
from tools.log import logger
from tools.env import InitEnv
from refreshMetadata import refresh_metadata


class PollingCaller:
    def __init__(self, POLL_INTERVAL: float):
        env = InitEnv()
        self.komgaAPI = env.komga
        self.interval = POLL_INTERVAL
        self.is_refreshing = False

    def start_polling(self):
        """启动服务"""
        def poll():
            while True:
                try:
                    if not self.is_refreshing:
                        series_added, series_added_number = self.komgaAPI.is_new_series_added()

                        if series_added:
                            logger.info(
                                f"检测到 {len(series_added_number)} 个系列更改")
                            # 死去的操作系统开始攻击我
                            self.is_refreshing = True
                            # 开始执行刷新脚本
                            refresh_metadata()
                            # 死去的操作系统停止攻击我
                            self.is_refreshing = False
                        else:
                            logger.info(f"{time.time()} 无新增内容")

                except Exception as e:
                    logger.error(f"轮询失败: {str(e)}", exc_info=True)
                    # 指数退避重试
                    retry_delay = min(2**self.interval, 60)
                    # 固定值重试
                    # retry_delay = self.interval
                    logger.warning(f"{retry_delay}秒后重试...")
                    time.sleep(retry_delay)
                    continue
                # 等待一个预设时间间隔
                time.sleep(self.interval)

        # 使用守护线程启动轮询
        threading.Thread(target=poll, daemon=True).start()


def main():
    # 20秒轮询一次
    POLL_INTERVAL = 20
    api_poller = PollingCaller(POLL_INTERVAL)
    api_poller.start_polling()

    # 防止服务主线程退出
    try:
        while True:
            time.sleep(65)
    except KeyboardInterrupt:
        logger.warning("服务手动终止: 退出BangumiKomga服务")


if __name__ == "__main__":
    main()
