"""Archive 服务入口 — 一行启动, 一行查询.

启动:
  service = start_archive_service()
  service.wait_ready(timeout=600)   # 等待首次数据就绪

查询 (任意模块):
  from bangumi_archive.archive_service import (
      archive_search_subjects,
      archive_get_subject_metadata,
      archive_get_related_subjects,
  )
  results = archive_search_subjects("早乙女")
  meta    = archive_get_subject_metadata(325236)
  related = archive_get_related_subjects(325236)

关闭:
  service.stop()
"""

import logging
from config.config import USE_BANGUMI_ARCHIVE
from bangumi_archive.archive_service import (
    ArchiveService,
    set_archive_service,
)

logger = logging.getLogger(__name__)


def start_archive_service() -> ArchiveService | None:
    """创建并启动 ArchiveService, 注入全局单例."""
    if not USE_BANGUMI_ARCHIVE:
        logger.debug("Bangumi Archive 未启用")
        return None

    service = ArchiveService()
    service.start()
    set_archive_service(service)
    return service
