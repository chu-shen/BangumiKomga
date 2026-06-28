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
    content_rowid='id',
    tokenize='trigram'
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

DDL_ARCHIVE_UPDATE = """
CREATE TABLE IF NOT EXISTS archive_update (
    key   TEXT PRIMARY KEY,
    value TEXT
)
"""

ALL_DDL = [DDL_SUBJECTS_IDX, DDL_FTS, DDL_RELATIONS, DDL_REL_INDEX, DDL_ARCHIVE_UPDATE]

# DB schema 版本号: 递增时 init_schema() 自动迁移.
# 使用模块级常量而非 f-string 拼接用户输入, 消除注入告警.
SCHEMA_VERSION = 3


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
        # 清理 WAL 残留文件 (-wal, -shm)
        for suffix in ("-wal", "-shm"):
            p = self._db_path + suffix
            if os.path.exists(p):
                try:
                    os.unlink(p)
                except OSError:
                    pass

    _SCHEMA_VERSION = SCHEMA_VERSION  # 兼容旧引用

    def init_schema(self):
        c = self._conn
        version = c.execute("PRAGMA user_version").fetchone()[0]
        if version >= self._SCHEMA_VERSION:
            return

        needs_fts_rebuild = False

        # v0→v2: 无 FTS5 或旧默认 tokenizer (porter), 重建
        if version <= 1:
            c.execute("DROP TABLE IF EXISTS subjects_fts")
            needs_fts_rebuild = True

        # v2→v3: meta 表重命名为 archive_update (语义更明确)
        if version <= 2:
            try:
                c.execute(
                    "ALTER TABLE meta RENAME TO archive_update"
                )
            except sqlite3.OperationalError:
                pass  # meta 不存在 (全新 db) 或已重命名

        for ddl in ALL_DDL:
            c.execute(ddl)
        # PRAGMA 不支持 ? 参数绑定 (Python sqlite3 限制),
        # SCHEMA_VERSION 为模块级 int 常量, 无 SQL 注入风险.
        c.execute(f"PRAGMA user_version = {int(SCHEMA_VERSION)}")
        c.commit()

        if needs_fts_rebuild:
            count = c.execute(
                "SELECT COUNT(*) FROM subjects_idx").fetchone()[0]
            if count > 0:
                logger.info(
                    "迁移 FTS5 至 trigram tokenizer, 重建全文索引 (%d 条)...",
                    count,
                )
                c.execute(
                    "INSERT INTO subjects_fts(rowid, name, name_cn) "
                    "SELECT id, name, name_cn FROM subjects_idx"
                )
                c.commit()
                logger.info("FTS5 迁移完成")

    # --- 构建 ------------------------------------------------------

    def build(self, subjects_path: str, relations_path: str):
        """导入 jsonlines → SQLite 索引 (单事务).

        只提取 id, type, name, name_cn + byte 偏移.
        """
        c = self._conn
        self.init_schema()

        logger.info("清空旧索引并开始事务构建...")
        c.execute("BEGIN")
        try:
            c.execute("DELETE FROM subjects_idx")
            c.execute("DELETE FROM subjects_fts")
            c.execute("DELETE FROM relations_idx")

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
            c.execute("COMMIT")
            logger.info("索引构建完成")
        except Exception:
            c.execute("ROLLBACK")
            raise

    def validate(self) -> bool:
        if self._conn is None:
            return False
        return (
            self._conn.execute(
                "SELECT COUNT(*) FROM subjects_idx").fetchone()[0] > 0
            and self._conn.execute(
                "SELECT COUNT(*) FROM relations_idx").fetchone()[0] > 0
        )

    def get_meta(self, key: str) -> Optional[str]:
        """读取 archive 更新时间 (如 last_updated)."""
        row = self._conn.execute(
            "SELECT value FROM archive_update WHERE key=?", (key,)
        ).fetchone()
        return row[0] if row else None

    def set_meta(self, key: str, value: str):
        """写入或更新 archive 更新时间."""
        self._conn.execute(
            "INSERT OR REPLACE INTO archive_update VALUES (?,?)", (key, value)
        )
        self._conn.commit()

    # --- 读接口 ----------------------------------------------------

    def _get_offsets_by_ids(self, ids: list[int]) -> dict[int, int]:
        """expand_sql 参数化 IN 查询: {id: row_offset}.

        所有值通过 ? 绑定传入 — 无 SQL 拼接.
        ids 来自 FTS5/LIKE 的参数化查询, 非用户输入.
        """
        if not ids:
            return {}
        sql, bound = expand_sql(
            "SELECT id, row_offset FROM subjects_idx WHERE id IN :ids",
            ids=ids,
        )
        rows = self._conn.execute(sql, bound).fetchall()
        return {r[0]: r[1] for r in rows}

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
        offsets = self._get_offsets_by_ids(ids)
        items = [_read_line_at_offset(self._mm, offsets[i])
                  for i in ids if i in offsets]
        return [item for item in items if item is not None]

    def search_all(self, query: str) -> list[dict]:
        """带子串回退的搜索: FTS 无结果时 fallback 到 LIKE.

        仅返回书籍 (type=1) 条目, 与 Bangumi API 的 filter={type:[1]} 保持一致.
        """
        if self._mm is None:
            return []
        results = self.search(query)
        if results:
            return [r for r in results if r is not None and r.get("type") == 1]
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
        offsets = self._get_offsets_by_ids(ids)
        items = [_read_line_at_offset(self._mm, offsets[i])
                  for i in ids if i in offsets]
        return [item for item in items if item is not None]

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
                            "INSERT INTO subjects_idx"
                            " (id, type, name, name_cn, row_offset)"
                            " VALUES (?,?,?,?,?)",
                            batch,
                        )
                        batch.clear()
                except Exception as e:
                    logger.warning(f"解析 subject 行失败: {e}")
                finally:
                    offset += len(line)
            if batch:
                c.executemany(
                    "INSERT INTO subjects_idx"
                    " (id, type, name, name_cn, row_offset)"
                    " VALUES (?,?,?,?,?)",
                    batch,
                )
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
                            "INSERT INTO relations_idx"
                            " (subject_id, relation_type, related_subject_id)"
                            " VALUES (?,?,?)",
                            batch,
                        )
                        batch.clear()
                except Exception as e:
                    logger.warning(f"解析 relation 行失败: {e}")
                    continue
            if batch:
                c.executemany(
                    "INSERT INTO relations_idx"
                    " (subject_id, relation_type, related_subject_id)"
                    " VALUES (?,?,?)",
                    batch,
                )
        return count


# --- 工具函数 -------------------------------------------------------

_IN_MARKER = re.compile(r":(\w+)")


def expand_sql(template: str, **params) -> tuple[str, tuple]:
    """将 :list 参数展开为 IN (?,?,?) 的纯参数化 SQL 生成器.

    模板中使用 ``:name`` 标记一个将由 params[name] list 填充的 IN 子句.
    其他值直接通过 ``?` 绑定 — 此函数只转换 `:name` 标记, 不改动现有 ``?``.

    返回 (expanded_sql, flat_params_tuple) 可直接传给 c.execute().

    示例:
        >>> sql, bound = expand_sql(
        ...     "SELECT id FROM t WHERE id IN :ids AND type = ?",
        ...     ids=[1, 2, 3],
        ... )
        >>> sql
        'SELECT id FROM t WHERE id IN (?,?,?) AND type = ?'
        >>> bound
        (1, 2, 3)

    安全保证: 只有 ``?`` 占位符插入模板字符串, 用户数据通过绑定元组传入.
    """
    expanded = template
    flattened = []
    for name in _IN_MARKER.findall(template):
        value = params.pop(name, None)
        if value is None:
            raise ValueError(f"expand_sql: 缺少参数 {name!r}")
        if not isinstance(value, (list, tuple)):
            raise TypeError(
                f"expand_sql: {name!r} 必须是 list/tuple, 收到 {type(value).__name__}")
        if not value:
            raise ValueError(f"expand_sql: {name!r} 不能为空")
        placeholders = ",".join("?" * len(value))
        expanded = expanded.replace(f":{name}", f"({placeholders})")
        flattened.extend(value)
    # 剩余 params (非 :name 标记的, 如果有) 追加到尾部供 ? 绑定
    flattened.extend(params.values())
    return expanded, tuple(flattened)


def _read_line_at_offset(mm: mmap.mmap, offset: int) -> Optional[dict]:
    """从 mmap 的指定偏移量读取一行 JSON."""
    try:
        mm.seek(offset)
        line = mm.readline().decode("utf-8", errors="ignore")
        return json.loads(line)
    except Exception:
        return None


def _fts_query(user_input: str) -> str:
    """将用户输入转换为 FTS5 查询 (trigram tokenizer).

    trigram 分词器对 CJK 和 Latin 均按 3-gram 切分, 无需区分语言.
    每个空白分隔的 term 追加 * 做前缀匹配, term 之间为 OR 语义.

    示例:
      魔法少女      → '"魔法少女"*'
      attack on titan → '"attack"* OR "on"* OR "titan"*'
      早乙女        → '"早乙女"*'
    """
    query = user_input.strip().replace('"', '""')
    if not query:
        return '""'
    terms = [f'"{t}"*' for t in query.split() if t]
    return ' OR '.join(terms) if terms else '""'
