# -*- coding: utf-8 -*- #
# ------------------------------------------------------------------
# Description: Bangumi API(https://github.com/bangumi/api)
# ------------------------------------------------------------------

import requests
from requests.adapters import HTTPAdapter

from api.bangumi_model import BangumiBaseType
import logging
logger = logging.getLogger(__name__)
from abc import ABC, abstractmethod
from typing import Optional

from tools.resort_search_results_list import resort_search_list
from tools.slide_window_rate_limiter import slide_window_rate_limiter
from zhconv import convert

# 延迟导入, 避免模块级循环依赖; 首次成功后缓存, 失败只报一次警告.
_archive_search_subjects = None
_archive_get_subject_metadata = None
_archive_get_related_subjects = None
_archive_is_ready = None
_archive_import_warned = False
_archive_disabled = False


def _ensure_archive_imported() -> bool:
    """确保 archive 模块已导入并缓存函数引用. 返回是否成功.

    首次 ImportError 后永久抑制重试: 模块查找失败是确定性的,
    进程不重启则环境不变, 反复尝试只会产生重复日志.
    USE_BANGUMI_ARCHIVE=False 时直接短路, 不触发 import 和日志.
    """
    global _archive_search_subjects, _archive_get_subject_metadata
    global _archive_get_related_subjects, _archive_is_ready
    global _archive_import_warned, _archive_disabled

    if _archive_search_subjects is not None:
        return True            # 已缓存
    if _archive_import_warned:
        return False           # 已失败过, 不重试
    if _archive_disabled:
        return False           # 配置明确禁用

    try:
        from config.config import USE_BANGUMI_ARCHIVE
        if not USE_BANGUMI_ARCHIVE:
            _archive_disabled = True
            return False
    except ImportError:
        pass  # config 不可用 (测试环境), 继续尝试导入 archive

    try:
        from bangumi_archive.archive_service import (
            archive_search_subjects,
            archive_get_subject_metadata,
            archive_get_related_subjects,
            archive_is_ready,
        )
        _archive_search_subjects = archive_search_subjects
        _archive_get_subject_metadata = archive_get_subject_metadata
        _archive_get_related_subjects = archive_get_related_subjects
        _archive_is_ready = archive_is_ready
        return True
    except ImportError as e:
        _archive_import_warned = True
        logger.warning(
            "无法导入 archive_service, 离线数据源不可用: %s",
            e, exc_info=True)
        return False




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
        url = f"{self.BASE_URL}/v0/search/subjects?limit=10"
        payload = {"keyword": query, "filter": {"type": [BangumiBaseType.BOOK.value]}}

        try:
            response = self.r.post(url, headers=self._get_headers(), json=payload)
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
            results = response_json["data"]

        return resort_search_list(
            query=query, results=results, threshold=threshold, is_novel=is_novel
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
            response = self.r.patch(url, headers=self._get_headers(), json=payload)
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
                image = self.get_subject_metadata(subject_metadata["id"])["images"][
                    image_size
                ]
            thumbnail = self.r.get(image).content
        except Exception as e:
            logger.error(f"出现错误: {e}")
            return []
        files = {"file": (subject_metadata["name"], thumbnail)}
        return files


class BangumiArchiveDataSource(DataSource):
    """离线数据源.

    infobox / platform / summary 等字段由 archive 原始 JSON 直接提供
    (标准 Bangumi 格式), 无需额外解析; 下游 process_metadata.py 直接
    从返回 dict 中读取.
    """

    def search_subjects(self, query, threshold=80, is_novel=False):
        if not _ensure_archive_imported() or not _archive_is_ready():
            return []
        results = _archive_search_subjects(query)
        for item in results:
            item["images"] = ""
            item["rating"] = {
                "rank": item.get("rank", 0),
                "total": item.get("total", 0),
                "count": item.get("score_details", {}),
                "score": item.get("score", 0.0),
            }
        return resort_search_list(
            query=query, results=results, threshold=threshold,
            is_novel=is_novel,
        )

    def get_subject_metadata(self, subject_id):
        if not _ensure_archive_imported() or not _archive_is_ready():
            return {}
        data = _archive_get_subject_metadata(subject_id)
        if not data:
            return {}
        try:
            data["images"] = ""
            data["rating"] = {
                "rank": data.get("rank", 0),
                "total": data.get("total", 0),
                "count": data.get("score_details", {}),
                "score": data.get("score", 0.0),
            }
            tags = data.get("tags", [])
            data["tags"] = [
                {"name": t["name"], "count": t.get("count", 0),
                 "total_cont": 0}
                for t in tags if isinstance(t, dict)
            ]
            data["total_episodes"] = data.get("eps", 0)
            favorite = data.get("favorite")
            if not isinstance(favorite, dict):
                favorite = {}
            data["collection"] = {
                "on_hold": favorite.get("on_hold", 0),
                "dropped": favorite.get("dropped", 0),
                "wish": favorite.get("wish", 0),
                "collect": favorite.get("done", 0),
                "doing": favorite.get("doing", 0),
            }
            data["meta_tags"] = [
                t["name"] for t in tags
                if isinstance(t, dict) and "name" in t
            ]
            return data
        except Exception as e:
            logger.error(f"构建Archive元数据出错: {e}")
            return {}

    def get_related_subjects(self, subject_id):
        if not _ensure_archive_imported() or not _archive_is_ready():
            return []
        return _archive_get_related_subjects(subject_id)

    def update_reading_progress(self, subject_id, progress):
        logger.warning("离线数据源不支持更新阅读进度 (%s)", subject_id)
        return False

    def get_subject_thumbnail(self, subject_metadata, image_size):
        logger.warning("离线数据源不支持获取封面 (%s)",
                       subject_metadata.get("id", "?"))
        return {}


class BangumiDataSourceFactory:
    """数据源工厂类."""

    @staticmethod
    def create(config):
        online = BangumiApiDataSource(config.get("access_token"))

        if config.get("use_local_archive", False):
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
            logger.debug(
                "主数据源: %s 失败，尝试备用数据源: %s",
                self.primary.__class__.__name__,
                self.secondary.__class__.__name__,
            )
            result = getattr(self.secondary, method_name)(*args, **kwargs)
        return result

    def search_subjects(self, query, threshold=80, is_novel=False):
        return self._fallback_call(
            "search_subjects", query, threshold=threshold, is_novel=is_novel
        )

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
