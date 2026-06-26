"""Archive 数据存储层 — SQLite 索引 + mmap 数据源 混合方案.

设计:
  subjects_idx:  只存 id, type, name, name_cn, row_offset (byte 偏移)
  subjects_fts:  FTS5 content 表, 索引 name/name_cn, 数据指向 subjects_idx
  relations_idx: 关联条目表 (subject_id, related_subject_id, relation_type)

读取时: SELECT offset → mmap seek → readline → json.loads → 返回完整 dict.
旧 pickle + mmap 方案中 pickle 34MB, 新 SQLite 索引 ~50MB (仅膨胀 ~16MB).

替代:
  - IndexedDataReader (pickle 单例 + mmap)
  - _search_line_batch_optimized (regex 离线回退)
"""

import json
import mmap
import os
import re
import sqlite3
from typing import Optional
import logging

logger = logging.getLogger(__name__)


# --- SQL DDL -------------------------------------------------------

DDL_SUBJECTS_IDX = """
CREATE TABLE IF NOT EXISTS subjects_idx (
    id         INTEGER PRIMARY KEY,
    type       INTEGER,
    name       TEXT,
    name_cn    TEXT,
    row_offset INTEGER NOT NULL
)
"""

DDL_FTS = """
CREATE VIRTUAL TABLE IF NOT EXISTS subjects_fts USING fts5(
    name,
    name_cn,
    content='subjects_idx',
    content_rowid='id'
)
"""

DDL_RELATIONS = """
CREATE TABLE IF NOT EXISTS relations_idx (
    subject_id         INTEGER NOT NULL,
    relation_type      TEXT,
    related_subject_id INTEGER NOT NULL
)
"""

DDL_REL_INDEX = """
CREATE INDEX IF NOT EXISTS idx_relations_subject
    ON relations_idx(subject_id)
"""

DDL_META = """
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT
)
"""

ALL_DDL = [DDL_SUBJECTS_IDX, DDL_FTS, DDL_RELATIONS, DDL_REL_INDEX, DDL_META]


# --- ArchiveDataStore -----------------------------------------------

class ArchiveDataStore:
    """SQLite 索引 + mmap 数据源.

    subjects_idx 表只存索引字段 + byte 偏移.
    完整 JSON 数据从 subject.jsonlines 通过 mmap 逐行读取.
    """

    def __init__(self, db_path: str, subjects_path: str):
        self._db_path = db_path
        self._subjects_path = subjects_path
        self._conn: Optional[sqlite3.Connection] = None
        self._mm: Optional[mmap.mmap] = None          # jsonlines mmap
        self._mm_file: Optional[object] = None         # file handle

    def open(self):
        """打开数据库 + mmap 数据文件."""
        self._conn = sqlite3.connect(self._db_path)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._conn.execute("PRAGMA cache_size=-32000")  # 32MB cache
        # 打开 jsonlines mmap
        if os.path.exists(self._subjects_path):
            self._mm_file = open(self._subjects_path, "rb")
            self._mm = mmap.mmap(
                self._mm_file.fileno(), 0, access=mmap.ACCESS_READ)

    def close(self):
        if self._mm:
            self._mm.close()
            self._mm = None
        if self._mm_file:
            self._mm_file.close()
            self._mm_file = None
        if self._conn:
            self._conn.close()
            self._conn = None

    def init_schema(self):
        c = self._conn
        for ddl in ALL_DDL:
            c.execute(ddl)
        c.commit()

    # --- 构建 ------------------------------------------------------

    def build(self, subjects_path: str, relations_path: str):
        """导入 jsonlines → SQLite 索引.

        只提取 id, type, name, name_cn + byte 偏移.
        """
        c = self._conn
        self.init_schema()

        logger.info("清空旧索引...")
        c.execute("DELETE FROM subjects_idx")
        c.execute("DELETE FROM subjects_fts")
        c.execute("DELETE FROM relations_idx")
        c.commit()

        # 1. 导入 subjects 索引字段 + 偏移
        logger.info("构建 subjects 索引 (仅元信息 + 偏移)...")
        total = self._import_subjects_idx(subjects_path)
        logger.info(f"subjects 索引: {total} 条")

        # 2. 导入 relations
        logger.info("构建 relations 索引...")
        rel_total = self._import_relations_idx(relations_path)
        logger.info(f"relations 索引: {rel_total} 条")

        # 3. 重建 FTS5
        logger.info("重建 FTS5 全文索引...")
        c.execute(
            "INSERT INTO subjects_fts(rowid, name, name_cn) "
            "SELECT id, name, name_cn FROM subjects_idx"
        )
        c.commit()
        logger.info("索引构建完成")

    def validate(self) -> bool:
        return self._conn.execute(
            "SELECT COUNT(*) FROM subjects_idx").fetchone()[0] > 0

    def get_meta(self, key: str) -> Optional[str]:
        """读取元信息 (如 last_updated 时间戳)."""
        row = self._conn.execute(
            "SELECT value FROM meta WHERE key=?", (key,)
        ).fetchone()
        return row[0] if row else None

    def set_meta(self, key: str, value: str):
        """写入或更新元信息."""
        self._conn.execute(
            "INSERT OR REPLACE INTO meta VALUES (?,?)", (key, value)
        )
        self._conn.commit()

    # --- 读接口 ----------------------------------------------------

    def get_by_id(self, subject_id: int) -> Optional[dict]:
        """通过 ID 获取完整 subject 数据."""
        if self._mm is None:
            return None
        row = self._conn.execute(
            "SELECT row_offset FROM subjects_idx WHERE id=?",
            (subject_id,),
        ).fetchone()
        if row is None:
            return None
        return _read_line_at_offset(self._mm, row[0])

    def search(self, query: str) -> list[dict]:
        """FTS5 全文搜索, 返回 name/name_cn 匹配的完整条目.

        FTS5 content 表指向 subjects_idx, MATCH 直接返回 rowid=id.
        """
        if self._mm is None:
            return []
        c = self._conn
        ids = [
            r[0] for r in c.execute(
                "SELECT rowid FROM subjects_fts WHERE subjects_fts MATCH ?",
                (_fts_query(query),),
            ).fetchall()
        ]
        if not ids:
            return []
        # 批量获取偏移 → mmap 读取
        placeholders = ",".join("?" * len(ids))
        offsets = {
            r[0]: r[1] for r in c.execute(
                f"SELECT id, row_offset FROM subjects_idx "
                f"WHERE id IN ({placeholders})",
                ids,
            ).fetchall()
        }
        return [_read_line_at_offset(self._mm, offsets[i])
                for i in ids if i in offsets]

    def search_all(self, query: str) -> list[dict]:
        """带子串回退的搜索: FTS 无结果时 fallback 到 LIKE."""
        if self._mm is None:
            return []
        results = self.search(query)
        if results:
            return [r for r in results if r.get("type") == 1]
        # FTS 无结果 — 回退 LIKE
        c = self._conn
        like = f"%{query}%"
        ids = [
            r[0] for r in c.execute(
                "SELECT id FROM subjects_idx WHERE type=1 "
                "AND (name LIKE ? OR name_cn LIKE ?)",
                (like, like),
            ).fetchall()
        ]
        if not ids:
            return []
        placeholders = ",".join("?" * len(ids))
        offsets = {
            r[0]: r[1] for r in c.execute(
                f"SELECT id, row_offset FROM subjects_idx "
                f"WHERE id IN ({placeholders})",
                ids,
            ).fetchall()
        }
        return [_read_line_at_offset(self._mm, offsets[i])
                for i in ids if i in offsets]

    def get_related(self, subject_id: int) -> list[dict]:
        """获取关联条目列表 (含 name/name_cn/type/id)."""
        c = self._conn
        rows = c.execute(
            "SELECT s.id, s.name, s.name_cn, s.type, r.relation_type "
            "FROM relations_idx r "
            "JOIN subjects_idx s ON r.related_subject_id = s.id "
            "WHERE r.subject_id = ?",
            (subject_id,),
        ).fetchall()
        return [
            {"id": r[0], "name": r[1], "name_cn": r[2],
             "type": r[3], "relation": r[4], "images": ""}
            for r in rows
        ]

    # --- 内部 ------------------------------------------------------

    def _import_subjects_idx(self, path: str) -> int:
        """只导入 id, type, name, name_cn + byte 偏移."""
        c = self._conn
        count = 0
        batch = []
        offset = 0
        with open(path, "rb") as f:
            for line in f:
                try:
                    item = json.loads(line.decode("utf-8"))
                    batch.append((
                        item.get("id"),
                        item.get("type"),
                        item.get("name"),
                        item.get("name_cn"),
                        offset,
                    ))
                    count += 1
                    if len(batch) >= 10000:
                        c.executemany(
                            "INSERT INTO subjects_idx VALUES (?,?,?,?,?)",
                            batch,
                        )
                        batch.clear()
                except Exception as e:
                    logger.warning(f"解析 subject 行失败: {e}")
                finally:
                    offset += len(line)
            if batch:
                c.executemany(
                    "INSERT INTO subjects_idx VALUES (?,?,?,?,?)",
                    batch,
                )
        c.commit()
        return count

    def _import_relations_idx(self, path: str) -> int:
        c = self._conn
        count = 0
        batch = []
        with open(path, "rb") as f:
            for line in f:
                try:
                    item = json.loads(line.decode("utf-8"))
                    batch.append((
                        item.get("subject_id"),
                        item.get("relation_type"),
                        item.get("related_subject_id"),
                    ))
                    count += 1
                    if len(batch) >= 10000:
                        c.executemany(
                            "INSERT INTO relations_idx VALUES (?,?,?)",
                            batch,
                        )
                        batch.clear()
                except Exception as e:
                    logger.warning(f"解析 relation 行失败: {e}")
                    continue
            if batch:
                c.executemany(
                    "INSERT INTO relations_idx VALUES (?,?,?)",
                    batch,
                )
        c.commit()
        return count


# --- 工具函数 -------------------------------------------------------

def _read_line_at_offset(mm: mmap.mmap, offset: int) -> Optional[dict]:
    """从 mmap 的指定偏移量读取一行 JSON."""
    try:
        mm.seek(offset)
        line = mm.readline().decode("utf-8", errors="ignore")
        return json.loads(line)
    except Exception:
        return None


def _fts_query(user_input: str) -> str:
    """将用户输入转换为 FTS5 查询.

    中文查询追加 * 通配符做前缀匹配.
    """
    query = user_input.strip().replace('"', '""')
    if not query:
        return '""'
    if any('\u4e00' <= c <= '\u9fff' for c in query):
        return f'"{query}"*'
    return f'"{query}"'


def parse_infobox(infobox_str: str) -> list:
    """解析 infobox 模板字符串 → [{"key":..., "value":...}, ...]."""
    if not infobox_str:
        return []
    infobox = []
    lines = infobox_str.split("\n")
    current_key = None
    current_value = []

    for line in lines:
        line = line.strip()
        if line.startswith("{{") or line.startswith("}}"):
            continue
        if line.startswith("|"):
            if current_key:
                infobox.append({
                    "key": current_key,
                    "value": _process_infobox_value(
                        current_key, " ".join(current_value)),
                })
            parts = line[1:].split("=", 1)
            if len(parts) == 2:
                current_key = parts[0].strip()
                current_value = [parts[1].strip()]
            else:
                current_key = None
        else:
            current_value.append(line)

    if current_key:
        infobox.append({
            "key": current_key,
            "value": _process_infobox_value(
                current_key, " ".join(current_value)),
        })
    return infobox


def _process_infobox_value(key, value_str):
    """处理特殊字段（别名、链接）."""
    if key == "别名":
        return [
            {"v": e.strip()}
            for e in RE_ARRAY_ENTRY.findall(value_str) if e.strip()
        ]
    if key == "链接":
        entries = []
        for raw in RE_ARRAY_ENTRY.findall(value_str):
            parts = raw.split("|", 1)
            if len(parts) >= 2:
                entries.append({"k": parts[0].strip(), "v": parts[1].strip()})
        return entries
    return value_str.strip()
