import os
import zipfile
import requests
import json
from config.config import ARCHIVE_FILES_DIR
from tools.log import logger
from bangumiArchive.indexedJsonlinesRead import IndexedDataReader
from tools.cacheTime import TimeCacheManager

# TODO: 加入Archive更新定时检查功能

UpdateTimeCacheFilePath = os.path.join(ARCHIVE_FILES_DIR, "archive_update_time.json")


def get_latest_url_and_time():
    """获取最新Archive文件下载地址"""
    try:
        response = requests.get(
            "https://raw.githubusercontent.com/bangumi/Archive/master/aux/latest.json",
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("browser_download_url"), data.get("updated_at")
    except requests.exceptions.RequestException as e:
        logger.warning(f"Bangumi Archive JSON 获取失败: {str(e)}")
    except json.JSONDecodeError as e:
        logger.warning(f"Bangumi Archive JSON 解析失败: {str(e)}")
    return "", ""


def update_index():
    filePaths = [
        os.path.join(ARCHIVE_FILES_DIR, filename)
        for filename in ["subject-relations.jsonlines", "subject.jsonlines"]
    ]
    for filePath in filePaths:
        archivefile = IndexedDataReader(filePath)
        if "relation" in archivefile:
            return archivefile.build_offsets_index(indexedFiled="subject_id")
        else:
            return archivefile.build_offsets_index(indexedFiled="id")
    return


def update_archive(url, target_dir=ARCHIVE_FILES_DIR):
    """下载并解压文件"""
    temp_zip_path = os.path.join(target_dir, "temp_archive.zip")
    # 也许应该加个下载进度条?
    logger.info("正在下载 Bangumi Archive 数据......")
    try:
        # 下载文件
        response = requests.get(url, stream=True, timeout=10)
        response.raise_for_status()
        with open(temp_zip_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        logger.info(f"Bangumi Archive 压缩包下载成功: {temp_zip_path}")

        # 解压文件
        with zipfile.ZipFile(temp_zip_path, "r") as zip_ref:
            zip_ref.extractall(target_dir)
        logger.info(f"Bangumi Archive 成功解压到: {target_dir}")

    except Exception as e:
        logger.error(f"Bangumi Archive 下载/解压失败: {str(e)}")
        return False
    finally:
        # 移除Archive压缩包
        if os.path.exists(temp_zip_path):
            os.remove(temp_zip_path)
    return True


def check_archive():
    os.makedirs(ARCHIVE_FILES_DIR, exist_ok=True)

    download_url, latest_update_time = get_latest_url_and_time()
    if download_url == "":
        logger.warning("无法获取 Bangumi Archive 下载链接, 跳过Archive更新")
        return

    # 读取本地缓存时间
    local_update_time = TimeCacheManager.convert_to_datetime(
        TimeCacheManager.read_time(UpdateTimeCacheFilePath)
    )
    remote_update_time = TimeCacheManager.convert_to_datetime(latest_update_time)
    if remote_update_time > local_update_time:
        logger.info("检测到新版本 Bangumi Archive, 开始更新...")
        if update_archive(download_url, ARCHIVE_FILES_DIR):
            update_index()
            TimeCacheManager.save_time(UpdateTimeCacheFilePath, latest_update_time)
            logger.info("Bangumi Archive 更新完成")
        else:
            logger.warning("Bangumi Archive 更新失败")
    else:
        logger.info("Bangumi Archive 已是最新数据, 无需更新")
