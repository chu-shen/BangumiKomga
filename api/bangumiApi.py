# -*- coding: utf-8 -*- #
# ------------------------------------------------------------------
# Description: Bangumi API(https://github.com/bangumi/api)
# ------------------------------------------------------------------


import requests
from requests.adapters import HTTPAdapter
from thefuzz import fuzz
from tools.log import logger
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

    def __init__(self, access_token=None, use_local_archive=False):
        self.r = requests.Session()
        self.r.mount('http://', HTTPAdapter(max_retries=3))
        self.r.mount('https://', HTTPAdapter(max_retries=3))
        self.access_token = access_token
        if self.access_token:
            self.refresh_token()
        self.use_local_archive = use_local_archive
        update_archive()

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

    def compute_name_score_by_fuzzy(self, name, name_cn, infobox, target):
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
                        score = max(
                            score, fuzz.ratio(alias["v"], target))
                else:
                    score = max(
                        score, fuzz.ratio(item["value"], target))
        return score

    def search_subjects_in_api(self, query):
        url = f"{self.BASE_URL}/search/subject/{quote_plus(query)}?responseGroup=small&type=1&max_results=25"
        # TODO 处理'citrus+ ~柑橘味香气plus~'
        try:
            response = self.r.get(url, headers=self._get_headers())
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            logger.error(f"An error occurred: {e}")
            return []
        return response

    def search_subjects(self, query, threshold=80):
        '''
        获取搜索结果，并移除非漫画系列。返回具有完整元数据的条目
        '''
        # 正面例子：魔女與使魔 -> 魔女与使魔，325236
        # 反面例子：君は淫らな僕の女王 -> 君は淫らな仆の女王，47331
        query = convert(query, 'zh-cn')

        # 看看Archive里面有没有数据
        if self.use_local_archive:
            response = search_subjects_in_archive(query)
            # 当Archive里面没有数据, 就试试在线API
            if response["results"] == 0 or 'title' in response.json():
                response = self.search_subjects_in_api(query)
        # 当不使用Archive时使用在线API
        else:
            response = self.search_subjects_in_api(query)
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

        # 具有完整元数据的排序条目，可提升结果准确性，但增加请求次数
        sort_results = []
        for result in results:
            manga_id = result['id']
            manga_metadata = self.get_subject_metadata(manga_id)
            if not manga_metadata:
                continue
            # bangumi书籍类型包括：漫画、小说、画集、其他
            # 由于komga不支持小说文字的读取，这里直接忽略`小说`类型，避免返回错误结果
            # bangumi书籍系列包括：系列、单行本
            # 此处需去除漫画系列的单行本，避免干扰，官方 API 已添加 series 字段（是否系列，仅对书籍类型的条目有效）
            # bangumi数据中存在单行本与系列未建立联系的情况
            if SubjectPlatform.parse(manga_metadata["platform"]) != SubjectPlatform.Novel and manga_metadata["series"]:
                # 计算得分
                score = self.compute_name_score_by_fuzzy(
                    manga_metadata["name"],
                    manga_metadata.get("name_cn", ""),
                    manga_metadata['infobox'],
                    query
                )
                # 仅添加得分超过阈值的条目
                if score >= threshold:
                    manga_metadata['fuzzScore'] = score
                    sort_results.append(manga_metadata)

        # 按得分降序排序
        sort_results.sort(key=lambda x: x['fuzzScore'], reverse=True)

        return sort_results

    def get_subject_metadata_in_api(self, subject_id):
        url = f"{self.BASE_URL}/v0/subjects/{subject_id}"
        try:
            response = self.r.get(url, headers=self._get_headers())
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            logger.error(f"An error occurred: {e}")
            logger.error(
                f"请检查 {subject_id} 是否填写正确；或属于 NSFW，但并未配置 BANGUMI_ACCESS_TOKEN")
            return []
        return response

    def get_subject_metadata(self, subject_id):
        '''
        获取漫画元数据
        '''
        # 看看Archive里面有没有数据
        if self.use_local_archive:
            response = get_subject_metadata_in_archive(subject_id)
            # Archive里面没有数据, 试试在线API
            if 'title' in response.json():
                response = self.get_subject_metadata_in_api(self, subject_id)
        # 当不使用Archive时使用在线API
        else:
            response = self.get_subject_metadata_in_api(self, subject_id)
        if response != []:
            return response.json()
        else:
            return response

    def get_related_subjects_in_api(self, subject_id):
        url = f"{self.BASE_URL}/v0/subjects/{subject_id}/subjects"
        try:
            response = self.r.get(url, headers=self._get_headers())
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            logger.error(f"An error occurred: {e}")
            return []
        return response

    def get_related_subjects(self, subject_id):
        '''
        获取漫画的关联条目
        '''
        # 看看Archive里面有没有数据
        if self.use_local_archive:
            response = get_related_subjects_in_archive(subject_id)
        # Archive里面没有数据, 试试在线API
            if 'title' in response.json():
                response = self.get_related_subjects_in_api(self, subject_id)
        # 当不使用Archive时使用在线API
        else:
            response = self.get_related_subjects_in_api(self, subject_id)
        if response != []:
            return response.json()
        else:
            return response

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

    def __init__(self):
        pass

    def search_subjects(self, query, threshold=80):
        """
        离线数据源搜索条目
        """
        return []

    def get_subject_metadata(self, subject_id):
        """
        离线数据源获取条目元数据
        """
        return {}

    def get_related_subjects(self, subject_id):
        """
        离线数据源获取关联条目
        """
        return []

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
