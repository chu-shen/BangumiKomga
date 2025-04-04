import os
import zipfile
import requests
import json
from datetime import datetime

# TODO: 加入Archive更新定时检查功能
# TODO: 加个下载/解压进度条
# TODO: 换成logger

ArchiveUpdateTime = None
ArchiveFilesPath = "../archivedata/"


def read_cache():
    """读取本地缓存时间"""
    try:
        with open("cache.json", "r") as f:
            return json.load(f).get("last_updated", "1970-01-01T00:00:00Z")
    except (FileNotFoundError, json.JSONDecodeError):
        return "1970-01-01T00:00:00Z"


def save_cache(last_updated):
    """保存最新成功时间"""
    with open("cache.json", "w") as f:
        json.dump({"last_updated": last_updated}, f)


def get_latest_url():
    """获取最新Archive文件下载地址"""
    try:
        response = requests.get(
            'https://raw.githubusercontent.com/bangumi/Archive/master/aux/latest.json',
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        global ArchiveUpdateTime
        ArchiveUpdateTime = data.get('updated_at')
        return data.get('browser_download_url')
    except requests.exceptions.RequestException as e:
        print(f"获取Bangumi Archive JSON失败: {str(e)}")
        return None
    except json.JSONDecodeError as e:
        print(f"Bangumi Archive JSON解析失败: {str(e)}")
        return None


def download_and_unzip(url, target_dir):
    """下载并解压文件"""
    temp_zip = 'temp_update.zip'
    print("正在下载 Bangumi Archive 数据......")
    try:
        # 下载文件
        response = requests.get(url, stream=True, timeout=10)
        response.raise_for_status()
        with open(temp_zip, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"Bangumi Archive 压缩包下载成功: {temp_zip}")

        # 解压文件
        with zipfile.ZipFile(temp_zip, 'r') as zip_ref:
            zip_ref.extractall(target_dir)
        print(f"Bangumi Archive 成功解压到: {target_dir}")

    except Exception as e:
        print(f"Bangumi Archive 下载/解压失败: {str(e)}")
        return False
    finally:
        if os.path.exists(temp_zip):
            os.remove(temp_zip)
    return True


def update_archive():
    target_dir = ArchiveFilesPath
    os.makedirs(target_dir, exist_ok=True)

    download_url = get_latest_url()
    if not download_url:
        print("无法获取 Bangumi Archive 下载链接")
        return

    global ArchiveUpdateTime
    # 读取本地缓存时间
    local_update_time = datetime.fromisoformat(
        read_cache().replace("Z", "+00:00"))
    remote_update_time = datetime.fromisoformat(
        ArchiveUpdateTime.replace("Z", "+00:00"))
    if remote_update_time > local_update_time:
        print("检测到新版本 Bangumi Archive, 开始更新...")
        if download_and_unzip(download_url, target_dir):
            save_cache(ArchiveUpdateTime)
            print("Bangumi Archive 更新完成")
        else:
            print("Bangumi Archive 更新失败")
    else:
        print("Bangumi Archive 已是最新数据, 无需更新")
