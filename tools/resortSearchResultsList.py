from thefuzz import fuzz
from api.bangumiModel import SubjectPlatform
from config.config import IS_NOVEL_ONLY


def compute_name_score_by_fuzzy(name, name_cn, infobox, target):
    """
    Use fuzzy to computes the Levenshtein distance between name, name_cn, and infobox "别名" (if exists) and the target string.
    """
    score = fuzz.ratio(name, target)
    if name_cn:
        score = max(score, fuzz.ratio(name_cn, target))
    for item in infobox:
        if item["key"] == "别名":
            if isinstance(item["value"], (list,)):  # 判断传入值是否为列表
                for alias in item["value"]:
                    score = max(score, fuzz.ratio(alias["v"], target))
            else:
                score = max(score, fuzz.ratio(item["value"], target))
    return score


def resort_search_list(query, results, threshold, DataSource):
    if len(results) < 1:
        return []
    # 构建具有完整元数据的排序条目
    sort_results = []
    for result in results:
        manga_id = result["id"]
        manga_metadata = DataSource.get_subject_metadata(manga_id)
        if not manga_metadata:
            continue
        # bangumi书籍系列包括：系列、单行本
        # 此处需去除漫画系列的单行本，避免干扰，官方 API 已添加 series 字段（是否系列，仅对书籍类型的条目有效）
        # bangumi数据中存在单行本与系列未建立联系的情况
        if not manga_metadata["series"]:
            continue
        # bangumi书籍类型包括：漫画、小说、画集、其他
        platform=SubjectPlatform.parse(manga_metadata["platform"])
        # 根据 IS_NOVEL_ONLY 配置判断是否只应用于 Komga 的小说库
        is_target_platform = (platform == SubjectPlatform.Novel) == IS_NOVEL_ONLY
        if is_target_platform:
            # 计算得分
            score = compute_name_score_by_fuzzy(
                manga_metadata["name"],
                manga_metadata.get("name_cn", ""),
                manga_metadata["infobox"],
                query,
            )
            # 仅添加得分超过阈值的条目
            if score >= threshold:
                manga_metadata["fuzzScore"] = score
                sort_results.append(manga_metadata)

    # 按得分降序排序
    sort_results.sort(key=lambda x: x["fuzzScore"], reverse=True)

    return sort_results
