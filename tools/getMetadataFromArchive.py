import re
import json
from tools.archiveAutoupdater import ArchiveFilesPath
from requests.models import Response
from io import BytesIO
from tools.log import logger

META_DATA_PATH = ArchiveFilesPath + "subject.jsonlines"
SUBJECT_RELATION_PATH = ArchiveFilesPath + "subject-relations.jsonlines"

# FUCK: 本地搜索竟然比在线慢很多你敢信
# TODO: 一次读一条jsonline性能太差了, 需要优化


# 匹配方括号列表的正则表达式
RE_ARRAY_ENTRY = re.compile(r'\[(.*?)\]')

# 条目类型
# https://bangumi.github.io/api/#/%E6%9D%A1%E7%9B%AE/getRelatedSubjectsBySubjectId
# 1 = book
# 2 = anime
# 3 = music
# 4 = game
# 6 = real
WHAT_IS_THE_TYPE = {
    1: "书籍",
    2: "动画",
    3: "音乐",
    4: "游戏",
    6: "三次元"
}


# TODO: 也许分块读入然后在内存里遍历?
def iterate_archive_lines(file_path: str):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_number, line in enumerate(f, 1):
                if not line:
                    continue  # 跳过空行
                try:
                    yield json.loads(line.strip())
                except json.JSONDecodeError as e:
                    logger.warning(f"Archive文件第 {line_number} 行解析失败: {str(e)}")
                    continue
    except FileNotFoundError:
        logger.error(f"Archive文件未找到: {file_path}")
    except Exception as e:
        logger.error(f"读取Archive发生错误: {str(e)}")


def pretend_it_is_response(data, status_code: int = 200) -> Response:

    response = Response()
    response.status_code = status_code
    response._content = json.dumps(data).encode('utf-8')
    response.raw = BytesIO(response._content)

    # 设置Content-Type头以便正确解析JSON
    response.headers['Content-Type'] = 'application/json'
    # 设置编码
    response.encoding = 'utf-8'

    return response


def parse_infobox(infobox_str):
    """解析infobox模板字符串"""
    infobox = []
    lines = infobox_str.split('\n')
    current_key = None
    current_value = []

    for line in lines:
        line = line.strip()
        if line.startswith('{{') or line.startswith('}}'):
            continue
        if line.startswith('|'):
            if current_key:
                processed_value = process_value(current_key, current_value)
                infobox.append({'key': current_key, 'value': processed_value})
            parts = line[1:].split('=', 1)
            if len(parts) == 2:
                current_key = parts[0].strip()
                current_value = parts[1].strip()
            else:
                current_key = None
        else:
            current_value += ' ' + line

    if current_key:
        processed_value = process_value(current_key, current_value)
        infobox.append({'key': current_key, 'value': processed_value})
    return infobox


def process_value(key, value_str):
    """处理特殊字段（如别名、链接）"""
    if key == '别名':
        entries = []
        for entry in RE_ARRAY_ENTRY.findall(value_str):
            cleaned = entry.strip()  # 去除前后空格
            if cleaned:
                entries.append({"v": cleaned})
        return entries
    if key == '链接':
        entries = []
        for raw_entry in RE_ARRAY_ENTRY.findall(value_str):
            parts = raw_entry.split('|', 1)  # 按第一个|分割
            if len(parts) >= 2:
                key = parts[0].strip()
                value = parts[1].strip()
                entries.append({"k": key, "v": value})
        return entries
    return value_str.strip()


def search_subject(keywords, item_type=1):
    results = []
    with open(META_DATA_PATH, "r", encoding="utf-8") as f:
        for line in f:
            try:
                item = json.loads(line.strip())
            except json.JSONDecodeError:
                continue

            # 类型过滤优先级高于关键词匹配
            if item_type and str(item.get("type", 0)) != str(item_type):
                continue

            # 多字段模糊匹配
            if (keywords.lower() in str(item["name"]).lower() or
                keywords.lower() in str(item.get("name_cn", "")).lower() or
                keywords in str(item.get("summary", "")) or
                    any(keywords in tag["name"] for tag in item.get("tags", []))):

                item = {
                    "id": item["id"],
                    "url": r"http://bgm.tv/subject/" + str(item["id"]),
                    "type": item.get("type", 0),
                    "name": item.get("name", ""),
                    "name_cn": item.get("name_cn", ""),
                    "summary": item.get("summary", ""),
                    "air_date": item.get("air_date", ""),
                    "air_weekday": item.get("air_weekday", 0),
                    # 离线Archive数据里根本没有这个┗|｀O′|┛ 嗷~~
                    "images": item.get("images", {})
                }

                results.append(item)
    return results


def get_metadata(subject_ID):
    with open(META_DATA_PATH, "r", encoding="utf-8") as f:
        for line in f:
            try:
                item = json.loads(line.strip())
            except json.JSONDecodeError:
                continue
             # 过滤ID
            if subject_ID == item.get("id", 0):
                return item
        return None


def get_related_subject_list(subject_ID):
    related_subjects = []
    with open(SUBJECT_RELATION_PATH, "r", encoding="utf-8") as f:
        for line in f:
            try:
                item = json.loads(line.strip())
            except json.JSONDecodeError:
                continue
             # 过滤ID
            if subject_ID == item.get("subject_id", 0):
                data = get_metadata(item.get("related_subject_id", 0))
                transformed = {
                    "name": data.get('name'),
                    "name_cn": data.get('name_cn'),
                    # 这里返回的类型的中文名, 但 subject-relations.jsonlines 里的 relation_type 字段我不明白代表什么含义, 所以就用 related_subject 里面的 type 来代替了
                    "relation": WHAT_IS_THE_TYPE[data.get('type')],
                    "id": data.get('id'),
                    "images": get_images(data.get('id'))
                }
                related_subjects.append(transformed)

        return related_subjects


# 如何使用本地数据获得封面仍然没有思路
def get_images(subject_ID):
    """示例固定值"""
    # return {
    #     "small": "https://lain.bgm.tv/r/200/pic/cover/l/17/43/472321_X1H4d.jpg",
    #     "grid": "https://lain.bgm.tv/r/100/pic/cover/l/17/43/472321_X1H4d.jpg",
    #     "large": "https://lain.bgm.tv/pic/cover/l/17/43/472321_X1H4d.jpg",
    #     "medium": "https://lain.bgm.tv/r/800/pic/cover/l/17/43/472321_X1H4d.jpg",
    #     "common": "https://lain.bgm.tv/r/400/pic/cover/l/17/43/472321_X1H4d.jpg"
    # }
    return {
        "small": "",
        "grid": "",
        "large": "",
        "medium": "",
        "common": ""
    }


# 等价于 /v0/subjects/{subject_id}
def get_subject_metadata_in_archive(subject_ID):
    data = get_metadata(subject_ID)
    if not data:
        return json.dumps({"error": "Subject not found in archive."}).encode("utf-8")

    try:
        transformed = {
            "date": data.get('date'),
            "platform": "漫画",  # 固定值或根据data['platform']映射
            "images": get_images(subject_ID),
            "summary": data.get('summary'),
            "name": data.get('name'),
            "name_cn": data.get('name_cn'),
            "tags": [{'name': t['name'], 'count': t['count'], 'total_cont': 0} for t in data.get('tags', [])],
            "infobox": parse_infobox(data['infobox']),
            "rating": {
                "rank": data.get('rank', 0),
                "total": data.get('total', 0),
                "count": data.get('score_details', {}),
                "score": data.get('score', 0.0)
            },
            "total_episodes": data.get('eps', 0),
            "collection": {
                "on_hold": data['favorite'].get('on_hold', 0),
                "dropped": data['favorite'].get('dropped', 0),
                "wish": data['favorite'].get('wish', 0),
                "collect": data['favorite'].get('done', 0),  # 假设done对应collect
                "doing": data['favorite'].get('doing', 0)
            },
            "id": data.get('id'),
            "eps": data.get('eps', 0),
            "meta_tags": [tag['name'] for tag in data.get('tags', [])],
            "volumes": data.get('volumes', 0),
            "series": data.get('series', False),
            "locked": data.get('locked', False),
            "nsfw": data.get('nsfw', False),
            "type": data.get('type', 0)
        }
        return pretend_it_is_response(transformed, 200)
    except Exception as e:
        return pretend_it_is_response({"error": str(e)}, 500)


# 等价于 /search/subject/{quote_plus(query)}?type=1
def search_subjects_in_archive(keywords):

    # 条目类型
    # 1 = book
    # 2 = anime
    # 3 = music
    # 4 = game
    # 6 = real
    item_type = 1

    # 执行搜索
    search_results = search_subject(
        keywords=keywords, item_type=item_type)

    # 构造返回值
    response = {
        "results": len(search_results),
        "list": search_results
    }

    return pretend_it_is_response(response)


# 等价于 /v0/subjects/{subject_id}/subjects
def get_related_subjects_in_archive(subject_ID):
    return pretend_it_is_response(get_related_subject_list(subject_ID))
