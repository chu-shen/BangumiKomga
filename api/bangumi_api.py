# -*- coding: utf-8 -*- #
# ------------------------------------------------------------------
# Description: Bangumi API(https://github.com/bangumi/api)
# ------------------------------------------------------------------

import requests
from requests.adapters import HTTPAdapter

from tools.log import logger
from bangumi_archive.local_archive_searcher import (
    parse_infobox,
    search_line,
    search_list,
    search_all_data,
)
from tools.resort_search_results_list import resort_search_list
from tools.slide_window_rate_limiter import slide_window_rate_limiter
from zhconv import convert
from urllib.parse import quote_plus
from abc import ABC, abstractmethod

# TODO： 在DataSource中添加一个本地缓存目录，将从 API 获取的封面图片保存为文件（如 cache/thumbnails/{subject_id}_{image_size}.jpg），下次直接读取本地文件，避免重复请求


class DataSource(ABC):
    """
    数据源基类
    """

    @abstractmethod
    def search_subjects(self, query, threshold=80, is_novel=False):
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
    def get_subject_thumbnail(self, subject_metadata, image_size):
        pass


class BangumiApiDataSource(DataSource):
    """
    Bangumi API 数据源类
    """

    BASE_URL = "https://api.bgm.tv"

    def __init__(self, access_token=None):
        self.r = requests.Session()
        self.r.mount("http://", HTTPAdapter(max_retries=3))
        self.r.mount("https://", HTTPAdapter(max_retries=3))
        self.access_token = access_token
        if self.access_token:
            self.refresh_token()

    def _get_headers(self):
        headers = {
            "User-Agent": "chu-shen/BangumiKomga (https://github.com/chu-shen/BangumiKomga)"
        }
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers

    def refresh_token(self):
        # https://bgm.tv/dev/app
        # https://next.bgm.tv/demo/access-token
        return

    @slide_window_rate_limiter()
    def search_subjects(self, query, threshold=80, is_novel=False):
        """
        获取搜索结果，并移除非漫画系列。返回具有完整元数据的条目
        """
        # 正面例子：魔女與使魔 -> 魔女与使魔，325236
        # 反面例子：君は淫らな僕の女王 -> 君は淫らな仆の女王，47331
        query = convert(query, "zh-cn")
        url = f"{self.BASE_URL}/search/subject/{quote_plus(query)}?responseGroup=small&type=1&max_results=25"
        # TODO 处理'citrus+ ~柑橘味香气plus~'
        try:
            response = self.r.get(url, headers=self._get_headers())
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            logger.error(f"出现错误: {e}")
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

        return resort_search_list(
            query=query, results=results, threshold=threshold, data_source=self, is_novel=is_novel
        )

    @slide_window_rate_limiter()
    def get_subject_metadata(self, subject_id):
        """
        获取漫画元数据
        """
        url = f"{self.BASE_URL}/v0/subjects/{subject_id}"
        try:
            response = self.r.get(url, headers=self._get_headers())
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            logger.error(f"An error occurred: {e}")
            logger.error(
                f"请检查 {subject_id} 是否填写正确；或属于 NSFW，但并未配置 BANGUMI_ACCESS_TOKEN"
            )
            return []
        return response.json()

    @slide_window_rate_limiter()
    def get_related_subjects(self, subject_id):
        """
        获取漫画的关联条目
        """
        url = f"{self.BASE_URL}/v0/subjects/{subject_id}/subjects"
        try:
            response = self.r.get(url, headers=self._get_headers())
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            logger.error(f"出现错误: {e}")
            return []
        return response.json()

    @slide_window_rate_limiter()
    def update_reading_progress(self, subject_id, progress):
        """
        更新漫画系列卷阅读进度
        """
        url = f"{self.BASE_URL}/v0/users/-/collections/{subject_id}"
        payload = {"vol_status": progress}
        try:
            response = self.r.patch(
                url, headers=self._get_headers(), json=payload)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            logger.error(f"出现错误: {e}")
        return response.status_code == 204

    @slide_window_rate_limiter()
    def get_subject_thumbnail(self, subject_metadata, image_size):
        """
        获取漫画封面

        image_size可选值:
        large, common, medium,small, grid
        """
        try:
            if subject_metadata["images"]:
                image = subject_metadata["images"][image_size]
            else:
                image = self.get_subject_metadata(subject_metadata["id"])[
                    "images"][image_size]
            thumbnail = self.r.get(image).content
        except Exception as e:
            logger.error(f"出现错误: {e}")
            return []
        files = {"file": (subject_metadata["name"], thumbnail)}
        return files


class BangumiArchiveDataSource(DataSource):
    """
    离线数据源类
    """

    def __init__(self, local_archive_folder):
        self.subject_relation_file = (
            local_archive_folder + "subject-relations.jsonlines"
        )
        self.subject_metadata_file = local_archive_folder + "subject.jsonlines"

    def _get_metadata_from_archive(self, subject_id):
        return search_line(
            file_path=self.subject_metadata_file,
            subject_id=subject_id,
            target_field="id",
        )

    def _get_relations_from_archive(self, subject_id):
        return search_list(
            file_path=self.subject_relation_file,
            subject_id=subject_id,
            target_field="subject_id",
        )

    # 将10s+的全文件扫描性能提升到1s左右
    def _get_search_results_from_archive(self, query):
        return search_all_data(
            file_path=self.subject_metadata_file, query=query
        )

    def search_subjects(self, query, threshold=80, is_novel=False):
        """
        离线数据源搜索条目
        """
        # 长度限制应搭配 threshold 使用, 于 resort_search_list() 中实现
        search_results = []
        results = self._get_search_results_from_archive(query)
        for item in results:
            if (
                query.lower() in str(item["name"]).lower()
                or query.lower() in str(item.get("name_cn", "")).lower()
                or query in str(item.get("summary", ""))
                or any(query in tag["name"] for tag in item.get("tags", []))
            ):
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
                    "images": "",
                }
                search_results.append(result)
        return resort_search_list(
            query=query, results=search_results, threshold=threshold, data_source=self, is_novel=is_novel
        )

    def get_subject_metadata(self, subject_id):
        """
        离线数据源获取条目元数据
        """
        data = self._get_metadata_from_archive(subject_id)
        if not data:
            return {}
        try:
            result = {
                "date": data.get("date"),
                "platform": data["platform"],
                # 忽略 images 字段
                # "images": get_images(subject_ID),
                "images": "",
                "summary": data.get("summary"),
                "name": data.get("name"),
                "name_cn": data.get("name_cn"),
                "tags": [
                    {"name": t["name"], "count": t["count"], "total_cont": 0}
                    for t in data.get("tags", [])
                ],
                "infobox": parse_infobox(data["infobox"]),
                "rating": {
                    "rank": data.get("rank", 0),
                    "total": data.get("total", 0),
                    "count": data.get("score_details", {}),
                    "score": data.get("score", 0.0),
                },
                "total_episodes": data.get("eps", 0),
                "collection": {
                    "on_hold": data["favorite"].get("on_hold", 0),
                    "dropped": data["favorite"].get("dropped", 0),
                    "wish": data["favorite"].get("wish", 0),
                    # 假设done对应collect
                    "collect": data["favorite"].get("done", 0),
                    "doing": data["favorite"].get("doing", 0),
                },
                "id": data.get("id"),
                "eps": data.get("eps", 0),
                "meta_tags": [tag["name"] for tag in data.get("tags", [])],
                "volumes": data.get("volumes", 0),
                "series": data.get("series", False),
                "locked": data.get("locked", False),
                "nsfw": data.get("nsfw", False),
                "type": data.get("type", 0),
            }
            return result
        except Exception as e:
            logger.error(f"构建Archive元数据出错: {e}")
            return {}

    def get_related_subjects(self, subject_id):
        """
        离线数据源获取关联条目列表
        """
        relation_list = self._get_relations_from_archive(subject_id)
        if not relation_list:
            return []
        result_list = []
        for item in relation_list:
            # 过滤ID
            if subject_id == item.get("subject_id", 0):
                try:
                    metadata = self._get_metadata_from_archive(
                        item.get("related_subject_id", 0)
                    )
                    result = {
                        "name": metadata.get("name"),
                        "name_cn": metadata.get("name_cn"),
                        "relation": item.get("relation_type"),
                        "id": metadata.get("id"),
                        # 忽略 images 字段
                        "images": "",
                    }
                    result_list.append(result)
                except Exception as e:
                    logger.error(f"构建Archive关联条目 {subject_id} 出错: {e}")
                    continue
        return result_list

    def update_reading_progress(self, subject_id, progress):
        """
        离线数据源更新阅读进度
        """
        NotImplementedError("离线数据源不支持更新阅读进度")
        return False

    def get_subject_thumbnail(self, subject_metadata, image_size):
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
        online = BangumiApiDataSource(config.get("access_token"))

        if config.get("use_local_archive", False):
            offline = BangumiArchiveDataSource(
                config.get("local_archive_folder"))
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
            logger.debug(
                "主数据源: %s 失败，尝试备用数据源: %s",
                self.primary.__class__.__name__,
                self.secondary.__class__.__name__,
            )
            result = getattr(self.secondary, method_name)(*args, **kwargs)
        return result

    def search_subjects(self, query, threshold=80, is_novel=False):
        return self._fallback_call("search_subjects", query, threshold=threshold, is_novel=is_novel)

    def get_subject_metadata(self, subject_id):
        return self._fallback_call("get_subject_metadata", subject_id)

    def get_related_subjects(self, subject_id):
        return self._fallback_call("get_related_subjects", subject_id)

    def update_reading_progress(self, subject_id, progress):
        self._fallback_call("update_reading_progress", subject_id, progress)

    def get_subject_thumbnail(self, subject_metadata, image_size):
        return self._fallback_call(
            "get_subject_thumbnail", subject_metadata, image_size
        )
