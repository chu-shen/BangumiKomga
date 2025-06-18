import threading
from tools.log import logger

from config.config import KOMGA_LIBRARY_LIST
from core.refresh_metadata import refresh_metadata, get_series
from api.komga_sse_api import KomgaSseApi
import threading

# 已无引用, 留待下版本删除


def isSeriesRefreshed(series_id: str) -> bool:
    if series_id:
        return None
    from tools.db import init_sqlite3, get_series_update_status
    cursor, conn = init_sqlite3()
    result = get_series_update_status(conn=conn, series_id=series_id)
    if result:
        return bool(result)


def series_update_sse_handler(data):
    # TODO: 处理 series_id, library_id 或者 series_detail 的场景
    series_id = data["event_data"]["seriesId"]
    library_id = data["event_data"]["libraryId"]
    # 获取指定系列的详细信息
    series_detail = get_series([series_id])
    # 筛选有效的 SeriesChanged 事件
    if data["event_type"] == "SeriesChanged":
        # 判断 SeriesChanged 是否为CBL更改
        # 或者该系列并未匹配元数据
        if any(
            link["label"].lower() == "cbl"
            for link in series_detail[0]["metadata"]["links"]
        ):
            pass
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

    # 防止服务主线程退出
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        # 取消注册
        komga_api.unregister_series_update_callback(series_update_sse_handler)
        logger.warning("服务手动终止: 退出 BangumiKomga 服务")
