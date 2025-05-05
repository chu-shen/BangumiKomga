from api.bangumiModel import SubjectRelation
from tools.getTitle import ParseTitle
import processMetadata
import json
import datetime
from tools.getNumber import getNumber, NumberType
from tools.env import *
from tools.log import logger
from tools.notification import send_notification
from tools.db import initSqlite3, record_series_status, record_book_status
from datetime import datetime, timedelta

env = InitEnv()
bgm = env.bgm
komga = env.komga
cursor, conn = initSqlite3()


def refresh_metadata(series_list=None):
    """
    刷新书籍系列元数据
    """
    if series_list is None or series_list == []:
        series_list = env.all_series

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
                logger.debug("use cbl %s for %s", subject_id, series_name)
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
                    logger.debug("skip falied series: %s", series_name)
                    continue

        # Use the bangumi API to search for the series by title on komga
        if subject_id == None:
            logger.debug("search for %s in bangumi", series_name)
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
            logger.warning("Failed to get metadata: %s", series_name)
            continue

        komga_metadata = processMetadata.setKomangaSeriesMetadata(
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
                thumbnail = bgm.get_subject_thumbnail(metadata)
                replace_thumbnail_result = komga.update_series_thumbnail(
                    series_id, thumbnail
                )
                if replace_thumbnail_result:
                    logger.debug(
                        "replace thumbnail for series: %s", series_name)
                else:
                    logger.error(
                        "Failed to replace thumbnail for series: %s", series_name
                    )
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


class ModifiedRecord:
    def __init__(self):
        self.records_file_name = "modified_records.json"
        self.records = self.load_records()

    def load_records(self) -> dict:
        try:
            with open(self.records_file_name, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def save_records(self, records):
        with open(self.records_file_name, "w") as f:
            json.dump(records, f)


def _filter_new_modified_metadata(seriesList, modified_records: dict):
    """
    过滤出新更改系列元数据
    """
    result = []
    for item in seriesList["content"]:
        if item["id"] in modified_records.keys():
            komga_modified_time = datetime.fromisoformat(
                item["lastModified"].replace("Z", "+00:00"))
            local_modified_time = datetime.fromisoformat(
                modified_records[item["id"]].replace("Z", "+00:00"))
            if komga_modified_time > local_modified_time:
                result.extend(item)
        else:
            result.extend(item)

    return result


def refresh_partial_metadata():
    """
    刷新部分书籍系列元数据
    """
    recent_modified_subjects = []
    modified_local_records = ModifiedRecord.records
    # 指定了 LIBRARY_ID
    if KOMGA_LIBRARY_LIST:
        for library in KOMGA_LIBRARY_LIST:
            page_index = 0
            while True:
                temp_series = komga.get_latest_series_with_libaryid(
                    library_id=library, page=page_index)
                new_add_series = _filter_new_modified_metadata(
                    temp_series, modified_records=modified_local_records)
                if new_add_series:
                    recent_modified_subjects.append(new_add_series)
                    # 更新分页状态
                    total_pages = temp_series["totalPages"]
                    if page_index + 1 >= total_pages:
                        break
                    page_index += 1
                else:
                    # 没有符合 _filter_new_modified_metadata 标准的新更改系列
                    break
    # 未指定 LIBRARY_ID
    else:
        page_index = 0
        while True:
            temp_series = komga.get_latest_series(page=page_index)
            new_add_series = _filter_new_modified_metadata(
                temp_series, modified_records=modified_local_records)
            if new_add_series:
                recent_modified_subjects.append(new_add_series)
                # 更新分页状态
                total_pages = temp_series["totalPages"]
                if page_index + 1 >= total_pages:
                    break
                page_index += 1
            else:
                # 没有符合 _filter_new_modified_metadata 标准的新更改系列
                break

    if recent_modified_subjects:
        refresh_metadata(recent_modified_subjects)
        updated_time = datetime.now()
        for recent_modified_subject in recent_modified_subjects:
            modified_local_records.records[recent_modified_subject["id"]
                                           ] = updated_time
        modified_local_records.save_records(modified_local_records)
    else:
        logger.info("未找到最近添加系列, 无需刷新")
    return


def update_book_metadata(book_id, related_subject, book_name, number):
    # Get the metadata for the book from bangumi
    book_metadata = processMetadata.setKomangaBookMetadata(
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
                logger.debug("replace thumbnail for book: %s", book_name)
            else:
                logger.error(
                    "Failed to replace thumbnail for book: %s", book_name)
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
                number, _ = getNumber(
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
                logger.debug("skip falied books: %s", book_name)
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
                number, _ = getNumber(subject["name"] + subject["name_cn"])
                try:
                    subjects_numbers.append(number)
                except ValueError:
                    logger.error(
                        "Failed to extract number: %s, %s, %s",
                        book_id,
                        subject["name"],
                        subject["name_cn"]
                    )

        # get nunmber from book name
        book_number, number_type = getNumber(book_name)
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


refresh_metadata()
