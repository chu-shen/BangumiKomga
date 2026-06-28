"""Archive 服务层 — 下载、更新、调度、读取统一入口.

替代旧的:
  - archive_autoupdater.py (函数式下载/更新)
  - periodic_archive_checker.py (daemon 线程 while True + time.sleep)
  - local_archive_searcher.py (索引回退模式)

架构:
  ArchiveService
    ├── _store: ArchiveDataStore (SQLite 读写)
    ├── _updater (后台线程): 首次下载 → 定时检查 GitHub
    └── 公开读接口: search / get_by_id / get_related
"""

import os
import sys
import threading
import time
import zipfile
import json
import logging
from typing import Optional

import requests

from config.config import (
    USE_BANGUMI_ARCHIVE,
    ARCHIVE_FILES_DIR,
    ARCHIVE_UPDATE_INTERVAL,
)
from bangumi_archive.archive_data_store import ArchiveDataStore
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


ARCHIVE_LATEST_URL = (
    "https://raw.githubusercontent.com/bangumi/Archive/master/aux/latest.json"
)
DB_PATH = os.path.join(ARCHIVE_FILES_DIR, "archive_index.db")
SUBJECTS_PATH = os.path.join(ARCHIVE_FILES_DIR, "subject.jsonlines")
RELATIONS_PATH = os.path.join(ARCHIVE_FILES_DIR, "subject-relations.jsonlines")

# 全局单例
_instance: Optional["ArchiveService"] = None
_instance_lock = threading.Lock()

# ---- 对外 API (archive_* 前缀, 供任意模块直接调用) ----------------

def _is_archive_enabled() -> bool:
    """USE_BANGUMI_ARCHIVE=False 时所有 archive_* 函数应在入口处短路."""
    return USE_BANGUMI_ARCHIVE


def archive_search_subjects(query: str) -> list[dict]:
    """离线搜索 Bangumi 条目, 返回 name/name_cn 匹配的完整 dict 列表."""
    if not _is_archive_enabled():
        return []
    srv = get_archive_service()
    return srv.search(query) if srv else []


def archive_get_subject_metadata(subject_id: int) -> Optional[dict]:
    """通过 subject_id 获取完整元数据 (mmap 直接读取)."""
    if not _is_archive_enabled():
        return None
    srv = get_archive_service()
    return srv.get_by_id(subject_id) if srv else None


def archive_get_related_subjects(subject_id: int) -> list[dict]:
    """获取关联条目列表 [{id, name, name_cn, type, relation}, ...]."""
    if not _is_archive_enabled():
        return []
    srv = get_archive_service()
    return srv.get_related(subject_id) if srv else []


def archive_is_ready() -> bool:
    """Archive 数据是否已就绪."""
    if not _is_archive_enabled():
        return False
    srv = get_archive_service()
    return srv is not None and srv.is_ready()

# --------------------------------------------------------------------

def get_archive_service() -> Optional["ArchiveService"]:
    with _instance_lock:
        return _instance


def set_archive_service(service: "ArchiveService"):
    global _instance
    with _instance_lock:
        _instance = service


class ArchiveService:
    """管理 archive 数据生命周期: 下载 → 导入 → 定期更新."""

    def __init__(self):
        self._store: Optional[ArchiveDataStore] = None
        self._store_lock = threading.Lock()
        self._running = False
        self._stop_event = threading.Event()
        self._ready_event = threading.Event()
        self._failed = False
        self._thread: Optional[threading.Thread] = None

    # -- 公开 API ----------------------------------------------------

    def start(self):
        """启动后台线程. 非阻塞, 用 wait_ready() 等待."""
        if not USE_BANGUMI_ARCHIVE:
            return
        if self._running:
            return
        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=False)
        self._thread.start()

    def stop(self):
        """停止服务, 等待当前周期结束."""
        self._running = False
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=30)
        with self._store_lock:
            if self._store is not None:
                self._store.close()
                self._store = None
        global _instance
        with _instance_lock:
            if _instance is self:
                _instance = None

    def wait_ready(self, timeout: Optional[float] = None) -> bool:
        """等待数据首次就绪 (once 模式使用)."""
        return self._ready_event.wait(timeout=timeout)

    def is_ready(self) -> bool:
        return self._ready_event.is_set() and not self._failed

    # -- 读代理 (线程安全: 锁内抓取 _store 引用, 锁外查询) ---------

    def _get_store(self) -> Optional[ArchiveDataStore]:
        with self._store_lock:
            return self._store

    def search(self, query: str) -> list[dict]:
        store = self._get_store()
        return store.search_all(query) if store else []

    def get_by_id(self, subject_id: int) -> Optional[dict]:
        store = self._get_store()
        return store.get_by_id(subject_id) if store else None

    def get_related(self, subject_id: int) -> list[dict]:
        store = self._get_store()
        return store.get_related(subject_id) if store else []

    # -- 内部 --------------------------------------------------------

    def _run(self):
        """后台主循环."""
        try:
            self._ensure_store()
            store = self._get_store()
            if store is None or not store.validate():
                self._download_and_rebuild()
            self._ready_event.set()
            self._poll_loop()
        except Exception:
            logger.error("Archive 服务初始化失败", exc_info=True)
            self._failed = True
            self._ready_event.set()  # 避免 wait_ready 永久阻塞, 但 is_ready() 返回 False

    def _ensure_store(self):
        os.makedirs(ARCHIVE_FILES_DIR, exist_ok=True)
        store = ArchiveDataStore(DB_PATH, SUBJECTS_PATH)
        store.open()
        store.init_schema()
        with self._store_lock:
            self._store = store

    def _download_and_rebuild(self):
        """下载 Archive → 解压 → 全量重建 SQLite 索引.

        构建到新的 ArchiveDataStore 实例, 然后原子替换 _store.
        读操作在重建期间不受影响 (继续使用旧 store).
        """
        logger.info("检查 Bangumi Archive 更新...")
        try:
            meta = _fetch_latest_meta()
        except Exception as e:
            logger.warning(f"无法获取 Archive 元数据: {e}")
            return

        download_url = meta.get("browser_download_url")
        if not download_url:
            logger.warning("未找到 Archive 下载链接")
            return

        remote_time = meta.get("updated_at", "")
        if self._is_up_to_date(remote_time):
            logger.info("Archive 已是最新数据, 无需更新")
            return

        logger.info(f"检测到新版本 Archive ({remote_time}), 开始下载...")
        zip_path = os.path.join(ARCHIVE_FILES_DIR, "temp_archive.zip")
        expected_size = meta.get("size")

        try:
            _download_archive(download_url, zip_path, expected_size)
            _extract_archive(zip_path, ARCHIVE_FILES_DIR)
        except Exception as e:
            logger.error(f"Archive 下载/解压失败: {e}")
            return
        finally:
            if os.path.exists(zip_path):
                os.remove(zip_path)

        # 解压完成后, 旧 mmap 仍有效 (mmap 不实时反映文件变更).
        # 以下构建新 store 并原子替换, 读者始终有有效 store.
        new_store = ArchiveDataStore(DB_PATH, SUBJECTS_PATH)
        try:
            new_store.open()
            new_store.build(SUBJECTS_PATH, RELATIONS_PATH)
            new_store.set_meta("last_updated", remote_time or "")
        except Exception:
            new_store.close()
            logger.error("索引构建失败, 保留旧数据")
            return

        # 原子替换
        with self._store_lock:
            old = self._store
            self._store = new_store
        if old is not None:
            old.close()
        logger.info("Archive 重建完成")

    def _is_up_to_date(self, remote_time: str) -> bool:
        """对比远程时间与 SQLite meta 中存储的本地更新时间."""
        store = self._get_store()
        local = store.get_meta("last_updated") if store else None
        if not local or not remote_time:
            return False
        try:
            local_dt = datetime.fromisoformat(local.replace("Z", "+00:00"))
            remote_dt = datetime.fromisoformat(remote_time.replace("Z", "+00:00"))
            return remote_dt <= local_dt
        except (ValueError, TypeError):
            return False

    def _poll_loop(self):
        """定时检查更新 (可中断)."""
        if ARCHIVE_UPDATE_INTERVAL <= 0:
            return
        interval = ARCHIVE_UPDATE_INTERVAL * 3600  # 小时 → 秒
        while self._running:
            if self._stop_event.wait(timeout=interval):
                break
            if not self._running:
                break
            try:
                self._download_and_rebuild()
            except Exception:
                logger.error("Archive 定时更新失败", exc_info=True)


# --- 工具函数 (从 archive_autoupdater 提取) -------------------------

def _fetch_latest_meta() -> dict:
    resp = requests.get(ARCHIVE_LATEST_URL, timeout=20)
    resp.raise_for_status()
    return resp.json()


def _download_archive(url: str, dest: str, expected_size=None):
    resp = requests.get(url, stream=True, timeout=10)
    resp.raise_for_status()
    total = expected_size or int(resp.headers.get("content-length", 0))

    # 仅在 TTY 且 tqdm 可用时使用进度条, 否则回退日志
    _use_tqdm = False
    if sys.stderr.isatty():
        try:
            import tqdm
            _use_tqdm = True
        except ImportError:
            logger.debug("tqdm 未安装, 回退到日志下载")

    if _use_tqdm:
        with open(dest, "wb") as f, tqdm.tqdm(
            total=total, unit="B", unit_scale=True, desc="下载中"
        ) as pbar:
            for chunk in resp.iter_content(chunk_size=8192):
                if not chunk:
                    continue
                f.write(chunk)
                pbar.update(len(chunk))
    else:
        logger.info(
            "开始下载 Archive (%.1f MB)...",
            total / 1024 / 1024 if total else 0,
        )
        with open(dest, "wb") as f:
            downloaded = 0
            last_log = 0
            for chunk in resp.iter_content(chunk_size=8192):
                if not chunk:
                    continue
                f.write(chunk)
                downloaded += len(chunk)
                if total > 0 and downloaded - last_log >= 10 * 1024 * 1024:
                    logger.info("下载进度: %.0f%%", downloaded / total * 100)
                    last_log = downloaded
        logger.info("Archive 下载完成")

    # 校验
    if expected_size and os.path.getsize(dest) != expected_size:
        raise IOError("下载文件大小不匹配")

    # ZIP CRC 自检
    _verify_zip(dest)


def _verify_zip(zip_path: str):
    with zipfile.ZipFile(zip_path) as zf:
        bad = zf.testzip()
        if bad is not None:
            raise IOError(f"压缩包损坏: {bad}")


def _extract_archive(zip_path: str, target_dir: str):
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(target_dir)
    logger.info(f"Archive 解压到: {target_dir}")
