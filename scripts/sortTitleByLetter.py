import sys, os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))
from tools.env import *
from tools.log import logger
from pypinyin import slug, Style

env = InitEnv()
komga = env.komga


def is_english_char(c):
    return "A" <= c <= "Z" or "a" <= c <= "z"


def sortTitleByLetter():
    """
    为存在`Bangumi`链接的系列在排序标题中添加首字母，使其能够在导航中按字母排序

    要求配置文件中`SORT_TITLE=True`

    脚本v0.9.1之后的版本已添加此功能，在配置文件中开启即可
    """
    if not SORT_TITLE:
        logger.info("未开启`SORT_TITLE`，退出")
        quit()

    series_list = []

    if KOMGA_LIBRARY_LIST and KOMGA_COLLECTION_LIST:
        logger.error("Use only one of KOMGA_LIBRARY_LIST or KOMGA_COLLECTION_LIST")
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
        if is_english_char(series["metadata"]["titleSort"][0]):
            logger.info(f"跳过：{series['metadata']['titleSort']}")
            continue
        for link in series["metadata"]["links"]:
            if link["label"].lower() == "bangumi":
                if is_english_char(series["metadata"]["title"][0]):
                    getFirstLetter = series["metadata"]["title"][0].upper()
                else:
                    getFirstLetter = slug(
                        series["metadata"]["title"][0],
                        errors="ignore",
                        style=Style.FIRST_LETTER,
                        separator="",
                    ).upper()

                if getFirstLetter:
                    titleSort = getFirstLetter + series["name"]
                    series_data = {"titleSort": titleSort}
                    komga.update_series_metadata(series["id"], series_data)
                    logger.info(f"排序标题修改为：{titleSort}")

                break


sortTitleByLetter()
