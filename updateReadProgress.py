from config.config import *
from tools.env import *
from tools.log import logger


def update_read_progress():
    """
    更新阅读进度
    """
    env = InitEnv()

    bgm = env.bgm
    komga = env.komga
    series_list = []

    if KOMGA_LIBRARY_LIST and KOMGA_COLLECTION_LIST:
        logger.error("KOMGA_LIBRARY_LIST 和 KOMGA_COLLECTION_LIST 只能配置一种")
    elif KOMGA_LIBRARY_LIST:
        series_list.extend(
            komga.get_series_with_libraryid(KOMGA_LIBRARY_LIST)["content"]
        )
    elif KOMGA_COLLECTION_LIST:
        series_list.extend(
            komga.get_series_with_collection(KOMGA_COLLECTION_LIST)["content"]
        )
    else:
        series_list = komga.get_all_series()["content"]

    for series in series_list:
        series_name = series["name"]

        books_read_count = series["booksReadCount"]
        try:
            for link in series["metadata"]["links"]:
                if link["label"].lower() == "bangumi":
                    subject_id = link["url"].split("/")[-1]
                    break
        except ValueError as e:
            logger.exception(e)
            logger.error("更新 " + series_name + " 的阅读进度失败")
            continue

        # TODO 添加是否同步判断逻辑，比如：是否`在读`
        if bgm.update_reading_progress(subject_id, books_read_count):
            logger.info(
                "成功更新系列: "
                + series_name
                + " 的阅读进度至: "
                + str(books_read_count)
            )
        else:
            logger.error(
                "无法将系列: "
                + series_name
                + " 的阅读进度更新至: "
                + str(books_read_count)
            )


update_read_progress()
