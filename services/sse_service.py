import threading
from tools.log import logger
from config.config import (
    KOMGA_LIBRARY_LIST,
)
from refreshMetadata import refresh_metadata, getSeries
from api.komgaSseApi import KomgaSseApi
import threading
import json


def series_update_sse_handler(data):
    event_data = json.loads(data["event_data"])
    series_id = event_data["seriesId"]
    library_id = event_data["libraryId"]
    # 获取指定系列的详细信息
    series_detail = getSeries([series_id])
    # 筛选有效的 SeriesChanged 事件
    if data["event_type"] == "SeriesChanged":
        # 判断 SeriesChanged 是否为CBL更改
        for link in series_detail["metadata"]["links"]:
            if link["label"].lower() == "cbl":
                continue
            else:
                # 无视其他 SeriesChanged 事件
                return
    # 其他事件 RefreshEventType, 例如 SeriesAdded
    else:
        pass
    # 设置了 KOMGA_LIBRARY_LIST 且 library_id 不在 KOMGA_LIBRARY_LIST 中
    if KOMGA_LIBRARY_LIST and (library_id not in KOMGA_LIBRARY_LIST):
        logger.info("未找到最近添加系列, 无需刷新")
    # 以 series_detail 刷新指定库中的系列
    else:
        refresh_metadata(series_detail)
    return


def sse_service():
    komga_api = KomgaSseApi()

    # 注册回调函数
    komga_api.register_series_update_callback(series_update_sse_handler)
    # 主线程保持运行（实际应用中可能有其他逻辑）
    # 防止服务主线程退出
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        # 取消注册
        komga_api.unregister_series_update_callback(series_update_sse_handler)
        logger.warning("服务手动终止: 退出 BangumiKomga 服务")
