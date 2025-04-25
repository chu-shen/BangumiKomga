# -*- coding: utf-8 -*- #
# ------------------------------------------------------------------
# Description: 处理komga漫画元数据
# ------------------------------------------------------------------


from api.bangumiModel import SubjectRelation
from api.komgaApi import *
from pypinyin import slug, Style

from config.config import SORT_TITLE


def __setTags(komga_metadata, bangumi_metadata):
    """
    漫画标签
    """
    taglist = []
    for info in bangumi_metadata["tags"]:
        if info["count"] >= 3:
            taglist.append(info["name"])

    komga_metadata.tags = taglist


def __setGenres(komga_metadata, bangumi_metadata):
    """
    漫画流派
    """
    genrelist = []
    # TODO bangumi并没有将漫画划分流派，后续可以考虑从tags中提取匹配
    if bangumi_metadata["platform"] is None:
        genrelist.append("其他")
    else:
        genrelist.append(bangumi_metadata["platform"])
    for info in bangumi_metadata["infobox"]:
        if info["key"] == "连载杂志":
            if type(info["value"]) == list:
                for v in info["value"]:
                    genrelist.append(v["v"])
            else:
                genrelist.append(info["value"])
    # TODO komga无评分/评级，暂时先将分数添加到流派字段中
    genrelist.append(str(round(bangumi_metadata["rating"]["score"])) + "分")

    komga_metadata.genres = genrelist


def __setStatus(komga_metadata, bangumi_metadata):
    """
    漫画连载状态
    """
    # TODO 判断漫画刊载情况
    runningLang = ["放送", "放送（連載）中"]
    abandonedLang = ["打ち切り"]
    endedLang = ["完結", "结束", "连载结束"]

    casestatus = "ONGOING"

    for info in bangumi_metadata["infobox"]:
        if info["key"] in runningLang:
            casestatus = "ONGOING"
        elif info["key"] in abandonedLang:
            casestatus = "ABANDONED"
            break
        elif info["key"] in endedLang:
            casestatus = "ENDED"
            break

    komga_metadata.status = casestatus


def __setTotalBookCount(komga_metadata, subjectRelations):
    """
    漫画总册数
    """
    totalBookCount = 0
    for relation in subjectRelations:
        # TODO 冷门漫画可能无关联条目，需要完善总册数判断逻辑
        if SubjectRelation.parse(relation["relation"]) == SubjectRelation.OFFPRINT:
            totalBookCount = totalBookCount + 1
    komga_metadata.totalBookCount = totalBookCount if totalBookCount != 0 else 1


def __setLanguage(komga_metadata, manga_filename):
    """
    本地漫画语言
    """
    languageTypes = ["日版"]
    for languageType in languageTypes:
        if languageType in manga_filename:
            komga_metadata.language = "ja-JP"


def __setAlternateTitles(komga_metadata, bangumi_metadata):
    """
    别名
    """
    alternateTitles = []
    title = {"label": "Original", "title": bangumi_metadata["name"]}
    alternateTitles.append(title)
    if bangumi_metadata["name_cn"] != "":
        title = {"label": "Bangumi", "title": bangumi_metadata["name_cn"]}
        alternateTitles.append(title)
    komga_metadata.alternateTitles = alternateTitles


def __setPublisher(komga_metadata, bangumi_metadata):
    """
    出版商
    """
    for info in bangumi_metadata["infobox"]:
        if info["key"] == "出版社":
            if isinstance(info["value"], (list,)):  # 判断传入值是否为列表
                # 只取第一个出版商
                for alias in info["value"]:
                    komga_metadata.publisher = alias["v"]
                    return
            else:
                # TODO 分割出版社：'集英社、東立出版社、新星出版社'
                komga_metadata.publisher = info["value"]
                return


def __setAgeRating(komga_metadata, bangumi_metadata):
    """
    分级
    """
    RATING_RULES = [
        {"tags": {"R18"}, "min_count": 10, "rating": 18},
        {"tags": {"R15", "工口", "卖肉", "福利"}, "min_count": 3, "rating": 15},
    ]

    ageRatings = []
    for tags in bangumi_metadata["tags"]:
        for rule in RATING_RULES:
            if tags["name"] in rule["tags"] and tags["count"] >= rule["min_count"]:
                ageRatings.append(rule["rating"])
                break

    if ageRatings:
        komga_metadata.ageRating = max(ageRatings)

    if bangumi_metadata["nsfw"]:
        komga_metadata.ageRating = 18


def __setTitle(komga_metadata, bangumi_metadata):
    """
    标题
    """
    # 优先使用中文标题
    if bangumi_metadata["name_cn"] != "":
        komga_metadata.title = bangumi_metadata["name_cn"]
    else:
        komga_metadata.title = bangumi_metadata["name"]


def is_english_char(c):
    return "A" <= c <= "Z" or "a" <= c <= "z"


def __setTitleSort(komga_metadata, manga_filename):
    """
    排序标题，额外添加首字母
    必须在修改标题(__setTitle)之后才能调用
    """
    komga_metadata.titleSort = manga_filename
    if SORT_TITLE:
        # 如果排序标题第一个为字母，则跳过
        if is_english_char(manga_filename[0]):
            komga_metadata.titleSort = manga_filename
            return
        # 如果标题第一个为字母，则直接使用标题第一个字母
        if is_english_char(komga_metadata.title[0]):
            getFirstLetter = komga_metadata.title[0].upper()
        # 中文转拼音首字母
        else:
            getFirstLetter = slug(
                komga_metadata.title[0],
                errors="ignore",
                style=Style.FIRST_LETTER,
                separator="",
            ).upper()
        if getFirstLetter:
            komga_metadata.titleSort = getFirstLetter + manga_filename


def __setSummary(komga_metadata, bangumi_metadata):
    """
    概要
    """
    komga_metadata.summary = bangumi_metadata["summary"]


def __setLinks(komga_metadata, bangumi_metadata, subjectRelations):
    """
    链接
    """
    links = [
        {
            "label": "Bangumi",
            "url": "https://bgm.tv/subject/" + str(bangumi_metadata["id"]),
        }
    ]
    for relation in subjectRelations:
        if relation["relation"] == "动画":
            link = {
                "label": "动画：" + relation["name"],
                "url": "https://bgm.tv/subject/" + str(relation["id"]),
            }
            links.append(link)
        if relation["relation"] == "书籍":
            link = {
                "label": "书籍：" + relation["name"],
                "url": "https://bgm.tv/subject/" + str(relation["id"]),
            }
            links.append(link)
    komga_metadata.links = links


def setKomangaSeriesMetadata(bangumiMetadata, mangaFileName, bgm):
    """
    获取漫画系列元数据
    """
    # init
    komangaSeriesMetadata = seriesMetadata()

    subjectRelations = bgm.get_related_subjects(bangumiMetadata["id"])

    # link
    __setLinks(komangaSeriesMetadata, bangumiMetadata, subjectRelations)

    # summary
    __setSummary(komangaSeriesMetadata, bangumiMetadata)

    # status
    __setStatus(komangaSeriesMetadata, bangumiMetadata)

    # genres
    __setGenres(komangaSeriesMetadata, bangumiMetadata)

    # tags
    __setTags(komangaSeriesMetadata, bangumiMetadata)

    # totalBookCount
    __setTotalBookCount(komangaSeriesMetadata, subjectRelations)

    # language
    __setLanguage(komangaSeriesMetadata, mangaFileName)

    # alternateTitles
    __setAlternateTitles(komangaSeriesMetadata, bangumiMetadata)

    # publisher
    __setPublisher(komangaSeriesMetadata, bangumiMetadata)

    # ageRating
    __setAgeRating(komangaSeriesMetadata, bangumiMetadata)

    # title
    __setTitle(komangaSeriesMetadata, bangumiMetadata)

    # titleSort
    __setTitleSort(komangaSeriesMetadata, mangaFileName)

    komangaSeriesMetadata.isvalid = True
    return komangaSeriesMetadata


def setKomangaBookMetadata(subject_id, number, name, bgm):
    """
    获取漫画单册元数据
    """

    komangaBookMetadata = bookMetadata()

    komangaBookMetadata.number = number
    komangaBookMetadata.numberSort = number

    # title 暂不做修改
    komangaBookMetadata.title = name

    bangumiMetadata = bgm.get_subject_metadata(subject_id)
    if not bangumiMetadata:
        return komangaBookMetadata

    subjectRelations = bgm.get_related_subjects(subject_id)
    # link
    __setLinks(komangaBookMetadata, bangumiMetadata, subjectRelations)
    # summary
    __setSummary(komangaBookMetadata, bangumiMetadata)
    # tags
    __setTags(komangaBookMetadata, bangumiMetadata)
    # authors
    authors = []
    for info in bangumiMetadata["infobox"]:
        if info["key"] == "作者":
            """
            基础格式：{'name':'值','role':'角色类型'}
            角色类型有：
                writer:作者
                inker:画图者
                translator:翻译者
                editor:主编
                cover:封面
                letterer:嵌字者
                colorist:上色者
                penciller:铅稿
                自定义的角色类型值
            """
            author = {"name": info["value"], "role": "writer"}
            authors.append(author)
    komangaBookMetadata.authors = authors
    # releaseDate
    komangaBookMetadata.releaseDate = bangumiMetadata["date"]
    # isbn
    for info in bangumiMetadata["infobox"]:
        if info["key"] == "ISBN":
            # ISBN必须是13位数
            # komangaBookMetadata.isbn = info["value"]
            continue
    komangaBookMetadata.isvalid = True
    return komangaBookMetadata
