import os
import zipfile
import requests
import json
from datetime import datetime
from config.config import ARCHIVE_FILES_DIR
from tools.log import logger

# TODO: 加入Archive更新定时检查功能

UpdateTimeCacheFilePath = os.path.join(ARCHIVE_FILES_DIR, "archive_update_time.json")


def read_cache_time():
    """读取本地更新时间"""
    try:
        with open(UpdateTimeCacheFilePath, "r") as f:
            return json.load(f).get("last_updated", "1970-01-01T00:00:00Z")
    except (FileNotFoundError, json.JSONDecodeError):
        return "1970-01-01T00:00:00Z"


def save_cache_time(last_updated):
    """保存最新成功时间"""
    with open(UpdateTimeCacheFilePath, "w") as f:
        json.dump({"last_updated": last_updated}, f)


def convert_to_datetime(update_time_string):
    try:
        result = datetime.fromisoformat(
            update_time_string.replace("Z", "+00:00"))
    except Exception as e:
        logger.warning(f"更新时间 {update_time_string} 获取失败: {str(e)}")
        return None
    return result


def get_latest_url_and_time():
    """获取最新Archive文件下载地址"""
    try:
        response = requests.get(
            'https://raw.githubusercontent.com/bangumi/Archive/master/aux/latest.json',
            timeout=20
        )
        response.raise_for_status()
        data = response.json()
        return data.get('browser_download_url'), data.get('updated_at')
    except requests.exceptions.RequestException as e:
        logger.warning(f"Bangumi Archive JSON 获取失败: {str(e)}")
    except json.JSONDecodeError as e:
        logger.warning(f"Bangumi Archive JSON 解析失败: {str(e)}")
    return "", ""


def update_archive(url, target_dir=ARCHIVE_FILES_DIR):
    """下载并解压文件"""
    temp_zip_path = os.path.join(target_dir, "temp_archive.zip")
    # 也许应该加个下载进度条?
    logger.info("正在下载 Bangumi Archive 数据......")
    try:
        # 下载文件
        response = requests.get(url, stream=True, timeout=10)
        response.raise_for_status()
        with open(temp_zip_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        logger.info(f"Bangumi Archive 压缩包下载成功: {temp_zip_path}")

        # 解压文件
        with zipfile.ZipFile(temp_zip_path, 'r') as zip_ref:
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
    local_update_time = convert_to_datetime(read_cache_time())
    remote_update_time = convert_to_datetime(latest_update_time)
    if remote_update_time > local_update_time:
        logger.info("检测到新版本 Bangumi Archive, 开始更新...")
        if update_archive(download_url, ARCHIVE_FILES_DIR):
            save_cache_time(latest_update_time)
            logger.info("Bangumi Archive 更新完成")
        else:
            logger.warning("Bangumi Archive 更新失败")
    else:
        logger.info("Bangumi Archive 已是最新数据, 无需更新")
