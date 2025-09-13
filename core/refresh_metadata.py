import os
from api.bangumi_model import SubjectRelation
from tools.get_title import ParseTitle
import core.process_metadata as process_metadata
from time import strftime, localtime
from tools.get_number import get_number, NumberType
from tools.env import *
from tools.log import logger
from tools.notification import send_notification
from tools.db import init_sqlite3, record_series_status, record_book_status
from tools.cache_time import TimeCacheManager


env = InitEnv()
bgm = env.bgm
komga = env.komga
cursor, conn = init_sqlite3()


def refresh_metadata(series_list=None):
    """
    刷新书籍系列元数据
    """
    if series_list is None or series_list == []:
        series_list = get_series()

    parse_title = ParseTitle()

    # 批量获取所有series_id
    series_ids = [series["id"] for series in series_list]
    # 执行一次查询获取所有series_id对应的记录
    series_records = cursor.execute(
        "SELECT * FROM refreshed_series WHERE series_id IN ({})".format(
            ",".join("?" for _ in series_ids)
        ),
        series_ids,
    ).fetchall()

    success_count = 0
    failed_count = 0
    success_comic = ""
    failed_comic = ""

    # Loop through each book series
    for series in series_list:
        series_id = series["id"]
        series_name = series["name"]

        # Get the subject id from the Correct Bgm Link (CBL) if it exists
        subject_id = None
        force_refresh_flag = False
        for link in series["metadata"]["links"]:
            if link["label"].lower() == "cbl":
                subject_id = int(link["url"].split("/")[-1])
                logger.debug("将 cbl %s 匹配于 %s", subject_id, series_name)
                # Get the metadata for the series from bangumi
                metadata = bgm.get_subject_metadata(subject_id)
                force_refresh_flag = True
                break

        if not force_refresh_flag:
            # 找到对应的series_record
            series_record = next(
                (record for record in series_records if record[0] == series_id), None
            )
            # series_record=c.execute("SELECT * FROM refreshed_series WHERE series_id=?", (series_id,)).fetchone()
            # Check if the series has already been refreshed
            if series_record:
                if series_record[2] == 1:
                    subject_id = cursor.execute(
                        "SELECT subject_id FROM refreshed_series WHERE series_id=?",
                        (series_id,),
                    ).fetchone()[0]
                    refresh_book_metadata(
                        subject_id, series_id, force_refresh_flag)
                    continue

                # recheck or skip failed series
                elif series_record[2] == 0 and not RECHECK_FAILED_SERIES:
                    logger.debug("跳过刮削失败的系列: %s", series_name)
                    continue

        # Use the bangumi API to search for the series by title on komga
        if subject_id == None:
            logger.debug("在 Bangumi 中搜索: %s ", series_name)
            title = parse_title.get_title(series_name)
            if title == None:
                failed_count, failed_comic = record_series_status(
                    conn,
                    series_id,
                    subject_id,
                    0,
                    series_name,
                    "None",
                    failed_count,
                    failed_comic,
                )
                continue
            search_results = bgm.search_subjects(title, FUZZ_SCORE_THRESHOLD)
            if len(search_results) > 0:
                subject_id = search_results[0]["id"]
                metadata = search_results[0]
            else:
                failed_count, failed_comic = record_series_status(
                    conn,
                    series_id,
                    subject_id,
                    0,
                    series_name,
                    "no subject in bangumi",
                    failed_count,
                    failed_comic,
                )
                continue

        if not metadata:
            logger.warning("无法获取元数据: %s", series_name)
            continue

        komga_metadata = process_metadata.set_komga_series_metadata(
            metadata, series_name, bgm
        )

        if komga_metadata.isvalid == False:
            failed_count, failed_comic = record_series_status(
                conn,
                series_id,
                subject_id,
                0,
                series_name,
                komga_metadata.title + " metadata invalid",
                failed_count,
                failed_comic,
            )
            continue

        series_data = {
            "status": komga_metadata.status,
            "summary": komga_metadata.summary,
            "publisher": komga_metadata.publisher,
            "genres": komga_metadata.genres,
            "tags": komga_metadata.tags,
            "title": komga_metadata.title,
            "alternateTitles": komga_metadata.alternateTitles,
            "ageRating": komga_metadata.ageRating,
            "links": komga_metadata.links,
            "totalBookCount": komga_metadata.totalBookCount,
            "language": komga_metadata.language,
            "titleSort": komga_metadata.titleSort,
        }

        # Update the metadata for the series on komga
        is_success = komga.update_series_metadata(series_id, series_data)
        if is_success:
            success_count, success_comic = record_series_status(
                conn,
                series_id,
                subject_id,
                1,
                series_name,
                komga_metadata.title,
                success_count,
                success_comic,
            )
            # 使用 Bangumi 图片替换原封面
            # 确保没有上传过海报，避免重复上传
            if (
                USE_BANGUMI_THUMBNAIL
                and len(komga.get_series_thumbnails(series_id)) == 0
            ):
                # 尝试多尺寸海报上传
                for thumbnail_size in ['large', 'common', 'medium']:
                    # 获取当前尺寸的封面
                    thumbnail = bgm.get_subject_thumbnail(
                        metadata, image_size=thumbnail_size)

                    # 尝试更新封面
                    replace_thumbnail_result = komga.update_series_thumbnail(
                        series_id, thumbnail)

                    if replace_thumbnail_result:
                        logger.debug("成功替换系列: %s 的海报", series_name)
                        # 成功则跳出海报更新循环
                        break
                    else:
                        logger.debug(
                            "以尺寸 %s 替换系列: %s 的海报失败，正在尝试下一个尺寸...",
                            thumbnail_size,
                            series_name,
                        )
                # 所有尺寸都失败时
                else:
                    logger.warning("替换系列: %s 的海报失败", series_name)
        else:
            failed_count, failed_comic = record_series_status(
                conn,
                series_id,
                subject_id,
                0,
                series_name,
                "komga update failed",
                failed_count,
                failed_comic,
            )
            continue

        refresh_book_metadata(subject_id, series_id, force_refresh_flag)

    # Add the series that failed to obtain metadata to the collection
    if CREATE_FAILED_COLLECTION:
        collection_name = "FAILED_COLLECTION"

        # TODO: 匹配错误的系列其update_success也是1, 需要找到一种方法将之筛选出来

        # 将db中update_success为0的series_ids筛选出来
        all_failed_series_ids = [
            row[0]
            for row in cursor.execute(
                "SELECT series_id FROM refreshed_series WHERE update_success = 0 and series_id IN ({})".format(
                    ",".join("?" for _ in series_ids)
                ),
                series_ids,
            ).fetchall()
        ]
        # 用all_failed_series_ids 创建 FAILED_COLLECTION
        if all_failed_series_ids:
            if komga.replace_collection(collection_name, True, all_failed_series_ids):
                logger.info("成功替换收藏: %s", collection_name)
            else:
                logger.error("替换收藏失败: %s", collection_name)

    logger.info(
        "执行完成! 刮削成功: %s 个, 刮削失败: %s 个", success_count, failed_count
    )
    send_notification(
        "已完成刷新！",
        "<font color='green'>已成功刷新："
        + str(success_count)
        + "</font> \n ---\n 包含以下条目：\n"
        + success_comic
        + "\n"
        + "<font color='red'>失败数："
        + str(failed_count)
        + "</font>\n\n包含以下条目：\n"
        + failed_comic
        + "\n"
        + strftime("%Y-%m-%d %H:%M:%S", localtime()),
    )


def get_series(series_ids=[]):
    series_list = []
    if len(series_ids) > 0:
        for series_id in series_ids:
            series_list.append(komga.get_specific_series(series_id))
    else:
        if KOMGA_LIBRARY_LIST and KOMGA_COLLECTION_LIST:
            logger.error("KOMGA_LIBRARY_LIST 和 KOMGA_COLLECTION_LIST 只能配置一种")
        elif KOMGA_LIBRARY_LIST:
            series_list.extend(
                komga.get_series_with_libraryid(KOMGA_LIBRARY_LIST)["content"]
            )
        elif KOMGA_COLLECTION_LIST:
            series_list.extend(
                komga.get_series_with_collection(
                    KOMGA_COLLECTION_LIST)["content"]
            )
        else:
            series_list = komga.get_all_series()["content"]
    return series_list


def _filter_new_modified_series(library_id=None):
    """
    过滤出新更改系列元数据
    """
    os.makedirs(ARCHIVE_FILES_DIR, exist_ok=True)
    # 读取上次修改时间
    LastModifiedCacheFilePath = os.path.join(
        ARCHIVE_FILES_DIR, "komga_last_modified_time.json"
    )
    local_last_modified = TimeCacheManager.convert_to_datetime(
        TimeCacheManager.read_time(LastModifiedCacheFilePath)
    )
    page_index = 0
    new_series = []
    stop_paging_flag = False
    while not stop_paging_flag:
        temp_series = komga.get_latest_series(
            library_id=library_id, page=page_index)

        if not temp_series:
            break

        for item in temp_series["content"]:
            komga_modified_time = TimeCacheManager.convert_to_datetime(
                item["lastModified"]
            )
            if komga_modified_time > local_last_modified:
                new_series.append(item)
            else:
                # 如果没有新更改的系列，停止分页
                stop_paging_flag = True
                break

        if not stop_paging_flag and (page_index + 1) < temp_series["totalPages"]:
            page_index += 1
        else:
            break

    return new_series


def refresh_partial_metadata():
    """
    刷新部分书籍系列元数据
    """
    # FIXME: 未处理有 cbl 的系列
    recent_modified_series = []
    # 指定了 LIBRARY_ID
    if KOMGA_LIBRARY_LIST:
        recent_modified_series.extend(
            _filter_new_modified_series(library_id=KOMGA_LIBRARY_LIST)
        )
    # FIXME: 未处理 collection
    else:
        recent_modified_series.extend(_filter_new_modified_series())

    if recent_modified_series:
        refresh_metadata(recent_modified_series)
        # 取第一个系列的 lastModified 时间作为新的更新时间
        LastModifiedCacheFilePath = os.path.join(
            ARCHIVE_FILES_DIR, "komga_last_modified_time.json"
        )
        TimeCacheManager.save_time(
            LastModifiedCacheFilePath,
            recent_modified_series[0]["lastModified"],
        )
    else:
        logger.info("未找到最近添加系列, 无需刷新")
    return


def update_book_metadata(book_id, related_subject, book_name, number):
    # Get the metadata for the book from bangumi
    book_metadata = process_metadata.set_komga_book_metadata(
        related_subject["id"], number, book_name, bgm
    )
    if book_metadata.isvalid == False:
        record_book_status(
            conn, book_id, related_subject["id"], 0, book_name, "metadata invalid"
        )
        return

    book_data = {
        "authors": book_metadata.authors,
        "summary": book_metadata.summary,
        "tags": book_metadata.tags,
        "title": book_metadata.title,
        "isbn": book_metadata.isbn,
        "number": book_metadata.number,
        "links": book_metadata.links,
        "releaseDate": book_metadata.releaseDate,
        "numberSort": book_metadata.numberSort,
    }

    # Update the metadata for the series on komga
    is_success = komga.update_book_metadata(book_id, book_data)
    if is_success:
        record_book_status(
            conn, book_id, related_subject["id"], 1, book_name, "")

        # 使用 Bangumi 图片替换原封面
        # 确保没有上传过海报，避免重复上传，排除 komga 生成的封面
        if (
            USE_BANGUMI_THUMBNAIL_FOR_BOOK
            and len(komga.get_book_thumbnails(book_id)) == 1
        ):
            thumbnail = bgm.get_subject_thumbnail(related_subject)
            replace_thumbnail_result = komga.update_book_thumbnail(
                book_id, thumbnail)
            if replace_thumbnail_result:
                logger.debug("替换书籍: %s 的海报 ", book_name)
            else:
                logger.error("替换书籍: %s 的海报失败", book_name)
    else:
        record_book_status(
            conn, book_id, related_subject["id"], 0, book_name, "komga update failed"
        )


def refresh_book_metadata(subject_id, series_id, force_refresh_flag):
    """
    刷新书元数据
    """
    if subject_id == None:
        return

    related_subjects = None
    subjects_numbers = []

    # Get all books in the series on komga
    books = komga.get_series_books(series_id)

    # 批量获取所有book_id
    book_ids = [book["id"] for book in books["content"]]

    c = conn.cursor()
    # 执行一次查询获取所有book_id对应的记录
    book_records = c.execute(
        "SELECT * FROM refreshed_books WHERE book_id IN ({})".format(
            ",".join("?" for _ in book_ids)
        ),
        book_ids,
    ).fetchall()

    # Loop through each book in the series on komga
    for book in books["content"]:
        book_id = book["id"]
        book_name = book["name"]

        # Get the subject id from the Correct Bgm Link (CBL) if it exists
        for link in book["metadata"]["links"]:
            if link["label"].lower() == "cbl":
                cbl_subject = bgm.get_subject_metadata(
                    link["url"].split("/")[-1])
                number, _ = get_number(
                    cbl_subject["name"] + cbl_subject["name_cn"])
                update_book_metadata(book_id, cbl_subject, book_name, number)
                break

        # 找到对应的book_record
        book_record = next(
            (record for record in book_records if record[0] == book_id), None
        )
        if book_record and not force_refresh_flag:
            if book_record[2] == 1:
                continue

            # recheck or skip failed book
            elif book_record[2] == 0 and not RECHECK_FAILED_BOOKS:
                logger.debug("跳过刮削失败的书籍: %s", book_name)
                continue

        # If related_subjects is still empty[], skip
        if related_subjects is None:
            # Get the related subjects for the series from bangumi
            related_subjects = [
                subject
                for subject in bgm.get_related_subjects(subject_id)
                if SubjectRelation.parse(subject["relation"])
                == SubjectRelation.OFFPRINT
            ]

            # Get the number for each related subject by finding the last number in the name or name_cn field
            subjects_numbers = []
            for subject in related_subjects:
                number, _ = get_number(subject["name"] + subject["name_cn"])
                try:
                    subjects_numbers.append(number)
                except ValueError:
                    logger.error(
                        "提取序号失败: %s, %s, %s",
                        book_id,
                        subject["name"],
                        subject["name_cn"],
                    )

        # get nunmber from book name
        book_number, number_type = get_number(book_name)
        ep_flag = True
        if number_type not in (NumberType.CHAPTER, NumberType.NONE):
            # Update the metadata for the book if its number matches a related subject number
            for i, number in enumerate(subjects_numbers):
                if book_number == number:
                    ep_flag = False

                    update_book_metadata(
                        book_id, related_subjects[i], book_name, number
                    )

                    break
        # 修正`话`序号
        if ep_flag:
            book_data = {"number": book_number, "numberSort": book_number}
            komga.update_book_metadata(book_id, book_data)
            record_book_status(
                conn, book_id, None, 0, book_name, "Only update book number"
            )
