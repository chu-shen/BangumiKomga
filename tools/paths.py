"""
Centralized path constants for the BangumiKomga project.

All runtime data paths (database, logs, archivedata) are defined here
so that every module uses the same PROJECT_ROOT-based absolute paths,
regardless of the current working directory.

Import this module freely — it has zero dependencies on other project modules.
"""
import os
import sqlite3
import shutil
import logging

_log = logging.getLogger(__name__)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATA_DIR = os.path.join(PROJECT_ROOT, "data")
LOG_DIR = os.path.join(DATA_DIR, "logs")
ARCHIVE_DIR = os.path.join(DATA_DIR, "archivedata")

DB_FILENAME = "recordsRefreshed.db"
DB_PATH = os.path.join(DATA_DIR, DB_FILENAME)

LOG_FILENAME = "refreshMetadata.log"


def ensure_runtime_layout():
    """
    确保运行时目录和文件布局就绪。

    幂等地创建所有运行时目录，并在 Docker bind-mount 将 DB_PATH
    误创建为目录时，安全地清理该目录并预创建数据库文件。
    所有启动时所需的物理准备都在此处完成。
    """
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)
    os.makedirs(ARCHIVE_DIR, exist_ok=True)

    if os.path.isdir(DB_PATH):
        _log.warning(
            "数据库路径为目录（可能由 Docker bind-mount 导致），正在删除: %s", DB_PATH
        )
        try:
            shutil.rmtree(DB_PATH)
        except OSError as e:
            _log.error("删除数据库目录失败: %s, 错误: %s", DB_PATH, e)
            raise RuntimeError(
                "无法删除数据库目录 %s，请手动删除后重试" % DB_PATH
            ) from e

    if not os.path.exists(DB_PATH):
        sqlite3.connect(DB_PATH).close()
