# -*- coding: utf-8 -*- #
# ------------------------------------------------------------------
# Description: Bangumi API(https://github.com/bangumi/api)
# ------------------------------------------------------------------


import requests
import json
from requests.adapters import HTTPAdapter

from tools.log import logger
from tools.archiveAutoupdater import update_archive
from tools.localArchiveHelper import parse_infobox
from tools.resortSearchResultsList import resort_search_list
from zhconv import convert
from urllib.parse import quote_plus
from abc import ABC, abstractmethod
from api.bangumiModel import SubjectPlatform, SubjectRelation


class DataSource(ABC):
    """
    数据源基类
    """
    @abstractmethod
    def search_subjects(self, query, threshold=80):
        pass

    @abstractmethod
    def get_subject_metadata(self, subject_id):
        pass

    @abstractmethod
    def get_related_subjects(self, subject_id):
        pass

    @abstractmethod
    def update_reading_progress(self, subject_id, progress):
        pass

    @abstractmethod
    def get_subject_thumbnail(self, subject_metadata):
        pass


class BangumiApiDataSource(DataSource):
    """
    Bangumi API 数据源类
    """
    BASE_URL = "https://api.bgm.tv"

    def __init__(self, access_token=None):
        self.r = requests.Session()
        self.r.mount('http://', HTTPAdapter(max_retries=3))
        self.r.mount('https://', HTTPAdapter(max_retries=3))
        self.access_token = access_token
        if self.access_token:
            self.refresh_token()

    def _get_headers(self):
        headers = {
            'User-Agent': 'chu-shen/BangumiKomga (https://github.com/chu-shen/BangumiKomga)'}
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers

    def refresh_token(self):
        # https://bgm.tv/dev/app
        # https://next.bgm.tv/demo/access-token
        return

    def search_subjects(self, query, threshold=80):
        '''
        获取搜索结果，并移除非漫画系列。返回具有完整元数据的条目
        '''
        # 正面例子：魔女與使魔 -> 魔女与使魔，325236
        # 反面例子：君は淫らな僕の女王 -> 君は淫らな仆の女王，47331
        query = convert(query, 'zh-cn')
        url = f"{self.BASE_URL}/search/subject/{quote_plus(query)}?responseGroup=small&type=1&max_results=25"
        # TODO 处理'citrus+ ~柑橘味香气plus~'
        try:
            response = self.r.get(url, headers=self._get_headers())
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            logger.error(f"An error occurred: {e}")
            return []

        # e.g. Artbooks.VOL.14 -> {"request":"\/search\/subject\/Artbooks.VOL.14?responseGroup=large&type=1","code":404,"error":"Not Found"}
        try:
            response_json = response.json()
        except ValueError as e:
            # bangumi无结果但返回正常
            logger.warning(f"{query}: 404 Not Found")
            return []
        else:
            # e.g. 川瀬绫 -> {"results":1,"list":null}
            if "list" in response_json and isinstance(response_json["list"], (list,)):
                results = response_json["list"]
            else:
                return []

        return resort_search_list(query=query, results=results, threshold=threshold, DataSource=self)

    def get_subject_metadata(self, subject_id):
        '''
        获取漫画元数据
        '''
        url = f"{self.BASE_URL}/v0/subjects/{subject_id}"
        try:
            response = self.r.get(url, headers=self._get_headers())
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            logger.error(f"An error occurred: {e}")
            logger.error(
                f"请检查 {subject_id} 是否填写正确；或属于 NSFW，但并未配置 BANGUMI_ACCESS_TOKEN")
            return []
        return response.json()

    def get_related_subjects(self, subject_id):
        '''
        获取漫画的关联条目
        '''
        url = f"{self.BASE_URL}/v0/subjects/{subject_id}/subjects"
        try:
            response = self.r.get(url, headers=self._get_headers())
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            logger.error(f"An error occurred: {e}")
            return []
        return response.json()

    def update_reading_progress(self, subject_id, progress):
        '''
        更新漫画系列卷阅读进度
        '''
        url = f"{self.BASE_URL}/v0/users/-/collections/{subject_id}"
        payload = {
            "vol_status": progress
        }
        try:
            response = self.r.patch(
                url, headers=self._get_headers(), json=payload)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            logger.error(f"An error occurred: {e}")
        return response.status_code == 204

    def get_subject_thumbnail(self, subject_metadata):
        '''
        获取漫画封面
        '''
        try:
            thumbnail = self.r.get(subject_metadata['images']['large']).content
        except requests.exceptions.RequestException as e:
            logger.error(f"An error occurred: {e}")
            return []
        files = {
            'file': (subject_metadata['name'], thumbnail)
        }
        return files


class BangumiArchiveDataSource(DataSource):
    """
    离线数据源类
    """

    # FUCK: 本地搜索竟然比在线慢很多你敢信
    # TODO: 一次读一条jsonline性能太差了, 需要优化

    def __init__(self, local_archive_folder):
        self.subject_relation_file = local_archive_folder + "subject-relations.jsonlines"
        self.subject_metadata_file = local_archive_folder + "subject.jsonlines"
        update_archive(local_archive_folder)

    def get_metadata_from_archive(self, subject_id):
        with open(self.subject_metadata_file, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    item = json.loads(line.strip())
                except json.JSONDecodeError:
                    continue
                # 过滤ID
                if subject_id == item.get("id", 0):
                    return item
        logger.error(f"Archive中不包含Subject_ID: {subject_id} 的元数据.")
        return None

    def search_subjects(self, query, threshold=80):
        """
        离线数据源搜索条目
        """
        # TODO: 当前未限制返回列表的长度
        results = []
        with open(self.subject_metadata_file, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    item = json.loads(line.strip())
                except json.JSONDecodeError:
                    continue

                # 优先进行类型过滤
                if str(item.get("type", 0)) != str(1):
                    continue

                # 多字段模糊匹配
                if (query.lower() in str(item["name"]).lower() or
                    query.lower() in str(item.get("name_cn", "")).lower() or
                    query in str(item.get("summary", "")) or
                        any(query in tag["name"] for tag in item.get("tags", []))):

                    result = {
                        "id": item["id"],
                        "url": r"http://bgm.tv/subject/" + str(item["id"]),
                        "type": item.get("type", 0),
                        "name": item.get("name", ""),
                        "name_cn": item.get("name_cn", ""),
                        "summary": item.get("summary", ""),
                        "air_date": item.get("air_date", ""),
                        "air_weekday": item.get("air_weekday", 0),
                        # 忽略 images 字段
                        "images": ""
                    }
                    results.append(result)

        return resort_search_list(query=query, results=results, threshold=threshold, DataSource=self)

    def get_subject_metadata(self, subject_id):
        """
        离线数据源获取条目元数据
        """
        data = self.get_metadata_from_archive(subject_id)
        try:
            result = {
                "date": data.get('date'),
                "platform": SubjectPlatform.parse(data["platform"]),
                # 忽略 images 字段
                # "images": get_images(subject_ID),
                "images": "",
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
                    # 假设done对应collect
                    "collect": data['favorite'].get('done', 0),
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
            return result
        except Exception as e:
            logger.error(f"构建Archive元数据出错: {e}")
            return {}

    def get_related_subjects(self, subject_id):
        """
        离线数据源获取关联条目列表
        """
        related_subjects = []
        with open(self.subject_relation_file, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    item = json.loads(line.strip())
                except json.JSONDecodeError:
                    continue
                # 过滤ID
                if subject_id == item.get("subject_id", 0):
                    try:
                        data = self.get_metadata_from_archive(
                            item.get("related_subject_id", 0))
                        result = {
                            "name": data.get('name'),
                            "name_cn": data.get('name_cn'),
                            "relation": SubjectRelation.parse(item.get('relation_type')),
                            "id": data.get('id'),
                            # 忽略 images 字段
                            # "images": get_images(data.get('id'))
                            "images": ""
                        }
                        related_subjects.append(result)
                    except Exception as e:
                        logger.error(f"构建Archive关联条目 {subject_id} 出错: {e}")
                        continue
            return related_subjects

    def update_reading_progress(self, subject_id, progress):
        """
        离线数据源更新阅读进度
        """
        NotImplementedError("离线数据源不支持更新阅读进度")
        return False

    def get_subject_thumbnail(self, subject_metadata):
        """
        离线数据源获取封面
        """
        NotImplementedError("离线数据源不支持获取封面")
        return {}


class BangumiDataSourceFactory:
    """
    数据源工厂类
    """
    @staticmethod
    def create(config):
        online = BangumiApiDataSource(config.get('access_token'))

        if config.get('use_local_archive', False):
            offline = BangumiArchiveDataSource()
            return FallbackDataSource(offline, online)

        return online


class FallbackDataSource(DataSource):
    """
    备用数据源类，用于在主数据源失败时使用备用数据源
    """

    def __init__(self, primary, secondary):
        self.primary = primary
        self.secondary = secondary

    def _fallback_call(self, method_name, *args, **kwargs):
        # 优先调用 primary 数据源的方法
        result = getattr(self.primary, method_name)(*args, **kwargs)

        # 如果结果为空/False（根据业务逻辑判断），则尝试 secondary 数据源
        if not result:
            result = getattr(self.secondary, method_name)(*args, **kwargs)
        return result

    def search_subjects(self, query, threshold=80):
        return self._fallback_call('search_subjects', query, threshold=threshold)

    def get_subject_metadata(self, subject_id):
        return self._fallback_call('get_subject_metadata', subject_id)

    def get_related_subjects(self, subject_id):
        return self._fallback_call('get_related_subjects', subject_id)

    def update_reading_progress(self, subject_id, progress):
        self._fallback_call('update_reading_progress', subject_id, progress)

    def get_subject_thumbnail(self, subject_metadata):
        return self._fallback_call('get_subject_thumbnail', subject_metadata)
