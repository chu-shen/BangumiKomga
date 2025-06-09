# -*- coding: utf-8 -*- #
# ------------------------------------------------------------------
# Description: 处理komga漫画元数据
# ------------------------------------------------------------------


from api.bangumi_model import SubjectRelation
from api.komga_api import *
from pypinyin import slug, Style

from config.config import SORT_TITLE


def _set_tags(komga_metadata, bangumi_metadata):
    """
    漫画标签
    """
    taglist = []
    for info in bangumi_metadata["tags"]:
        if info["count"] >= 3:
            taglist.append(info["name"])

    komga_metadata.tags = taglist


def _set_genres(komga_metadata, bangumi_metadata):
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


def _set_status(komga_metadata, bangumi_metadata):
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


def _set_total_book_count(komga_metadata, subject_relations):
    """
    漫画总册数
    """
    totalBookCount = 0
    for relation in subject_relations:
        # TODO 冷门漫画可能无关联条目，需要完善总册数判断逻辑
        if SubjectRelation.parse(relation["relation"]) == SubjectRelation.OFFPRINT:
            totalBookCount = totalBookCount + 1
    komga_metadata.totalBookCount = totalBookCount if totalBookCount != 0 else 1


def _set_language(komga_metadata, manga_filename):
    """
    本地漫画语言

    根据文件名中的关键字设置漫画语言，后续分组会覆盖前面的匹配结果
    """
    languageTypes = [
        ("ja-JP", ["日版"]),
        ("zh-Hans", ["bili", "B漫", "汉化", "简中"]),
        (
            "zh-Hant",
            [
                "繁中",
                "尖端",
                "东立",
                "東立",
                "东贩",
                "東販",
                "玉皇朝",
                "天下",
                "青文",
                "长鸿",
                "角川",
                "文传",
                "文傳",
                "時報",
            ],
        ),
    ]
    for langCode, keywords in languageTypes:
        if any(keyword in manga_filename for keyword in keywords):
            komga_metadata.language = langCode

def _set_alternate_titles(komga_metadata, bangumi_metadata):
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


def _set_publisher(komga_metadata, bangumi_metadata):
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


def _set_age_rating(komga_metadata, bangumi_metadata):
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


def _set_title(komga_metadata, bangumi_metadata):
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


def _set_title_sort(komga_metadata, manga_filename):
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


def _set_summary(komga_metadata, bangumi_metadata):
    """
    概要
    """
    komga_metadata.summary = bangumi_metadata["summary"]


def _set_links(komga_metadata, bangumi_metadata, subject_relations):
    """
    链接
    """
    links = [
        {
            "label": "Bangumi",
            "url": "https://bgm.tv/subject/" + str(bangumi_metadata["id"]),
        }
    ]
    for relation in subject_relations:
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


def set_komga_series_metadata(bangumi_metadata, manga_filename, bgm):
    """
    获取漫画系列元数据
    """
    # init
    komga_series_metadata = SeriesMetadata()

    subject_relations = bgm.get_related_subjects(bangumi_metadata["id"])

    # link
    _set_links(komga_series_metadata, bangumi_metadata, subject_relations)

    # summary
    _set_summary(komga_series_metadata, bangumi_metadata)

    # status
    _set_status(komga_series_metadata, bangumi_metadata)

    # genres
    _set_genres(komga_series_metadata, bangumi_metadata)

    # tags
    _set_tags(komga_series_metadata, bangumi_metadata)

    # totalBookCount
    _set_total_book_count(komga_series_metadata, subject_relations)

    # language
    _set_language(komga_series_metadata, manga_filename)

    # alternateTitles
    _set_alternate_titles(komga_series_metadata, bangumi_metadata)

    # publisher
    _set_publisher(komga_series_metadata, bangumi_metadata)

    # ageRating
    _set_age_rating(komga_series_metadata, bangumi_metadata)

    # title
    _set_title(komga_series_metadata, bangumi_metadata)

    # titleSort
    _set_title_sort(komga_series_metadata, manga_filename)

    komga_series_metadata.isvalid = True
    return komga_series_metadata


def set_komga_book_metadata(subject_id, number, name, bgm):
    """
    获取漫画单册元数据
    """

    komga_book_metadata = BookMetadata()

    komga_book_metadata.number = number
    komga_book_metadata.numberSort = number

    # title 暂不做修改
    komga_book_metadata.title = name

    bangumi_metadata = bgm.get_subject_metadata(subject_id)
    if not bangumi_metadata:
        return komga_book_metadata

    subject_relations = bgm.get_related_subjects(subject_id)
    # link
    _set_links(komga_book_metadata, bangumi_metadata, subject_relations)
    # summary
    _set_summary(komga_book_metadata, bangumi_metadata)
    # tags
    _set_tags(komga_book_metadata, bangumi_metadata)
    # authors
    authors = []
    for info in bangumi_metadata["infobox"]:
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
    komga_book_metadata.authors = authors
    # releaseDate
    komga_book_metadata.releaseDate = bangumi_metadata["date"]
    # isbn
    for info in bangumi_metadata["infobox"]:
        if info["key"] == "ISBN":
            # ISBN必须是13位数
            # komangaBookMetadata.isbn = info["value"]
            continue
    komga_book_metadata.isvalid = True
    return komga_book_metadata
