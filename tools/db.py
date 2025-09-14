import sqlite3
from time import strftime, localtime
from tools.log import logger


def upsert_series_record(
    conn, series_id, subject_id, update_success, series_name, bangumi_name
):
    """
    插入或更新数据记录
    :param conn: 数据库连接
    :param table: 表名
    :param series_id: komga id
    :param subject_id: bangumi id
    :param update_success: 更新是否成功
    :param series_name: komga名称
    :param refresh_time: 刷新时间
    :param bangumi_name: bangumi名称
    """
    c = conn.cursor()
    # 0 (false) and 1 (true)
    c.execute(
        "INSERT OR REPLACE INTO refreshed_series (series_id,subject_id,update_success,series_name,bangumi_name,refresh_time) VALUES (?,?,?,?,?,?)",
        (
            series_id,
            subject_id,
            update_success,
            series_name,
            bangumi_name,
            strftime("%Y-%m-%d %H:%M:%S", localtime()),
        ),
    )
    conn.commit()


def upsert_book_record(conn, book_id, subject_id, update_success, book_name):
    c = conn.cursor()
    # 0 (false) and 1 (true)
    c.execute(
        "INSERT OR REPLACE INTO refreshed_books (book_id,subject_id,update_success,book_name,refresh_time) VALUES (?,?,?,?,?)",
        (
            book_id,
            subject_id,
            update_success,
            book_name,
            strftime("%Y-%m-%d %H:%M:%S", localtime()),
        ),
    )
    conn.commit()


def init_sqlite3():
    # Create a connection to the sqlite database
    conn = sqlite3.connect("recordsRefreshed.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS refreshed_series (series_id text primary key,subject_id text ,update_success BOOLEAN,series_name text,bangumi_name text,refresh_time text )"""
    )
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS refreshed_books (book_id text primary key,subject_id text ,update_success BOOLEAN,book_name text,refresh_time text )"""
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_series_id ON refreshed_series(series_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_subject_id ON refreshed_series(subject_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_book_id ON refreshed_books(book_id)")
    return cursor, conn


def record_series_status(
    conn, series_id, subject_id, status, series_name, message, count, comic
):
    upsert_series_record(conn, series_id, subject_id,
                         status, series_name, message)
    count += 1
    if status == 0:
        logger.warning("更新系列元数据失败: " + series_name + ", " + message)
        comic = comic + "- " + series_name + "\n"
    elif status == 1:
        logger.info("更新系列元数据成功: " + series_name + ", " + message)
        comic = comic + "- " + message + "\n"

    return count, comic


def record_book_status(conn, book_id, subject_id, status, book_name, message):
    upsert_book_record(conn, book_id, subject_id, status, book_name)
    if status == 0:
        logger.warning("更新书籍元数据失败: " + book_name + ", " + message)
    elif status == 1:
        logger.info("更新书籍元数据成功: " + book_name)


def get_series_update_status(conn, series_id):
    """
    查询指定 series_id 的 update_success 状态
    """
    cursor = conn.cursor()
    cursor.execute(
        "SELECT update_success FROM refreshed_series WHERE series_id = ?",
        (series_id,)
    )
    result = cursor.fetchone()
    if result:
        return result[0]
    else:
        return None
