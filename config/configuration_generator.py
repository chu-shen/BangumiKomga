# configuration_generator.py
import re
import ast
import os
import getpass
import json
import requests
from colorama import Fore, Style, init
from requests.exceptions import RequestException
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))
from api.komga_api import KomgaApi

# 初始化 colorama（Windows 必需）
init()

# 全局常量
MAX_RETRIES = 3
TIMEOUT = 20
USER_AGENT = "chu-shen/BangumiKomga (https://github.com/chu-shen/BangumiKomga)"

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_FILE = os.path.join(PROJECT_ROOT, "config", "config.template.py")
OUTPUT_FILE = os.path.join(PROJECT_ROOT, "config", "config.generated.py")
PRESENT_FILE = os.path.join(PROJECT_ROOT, "config", "config.py")


def validate_email(email):
    """邮箱格式验证"""
    return re.match(r"[^@]+@[^@]+\.[^@]+", email) is not None


def validate_url(url):
    """URL格式验证"""
    return url.startswith(("http://", "https://"))


def validate_bangumi_token(token):
    """验证BGM访问令牌有效性"""
    headers = {"User-Agent": USER_AGENT, "Authorization": f"Bearer {token}"}
    try:
        colored_message("🔗 正在验证BGM令牌...", Fore.YELLOW)
        session = requests.Session()
        test_URL = "https://api.bgm.tv/v0/me"
        response = session.get(test_URL, headers=headers, timeout=TIMEOUT)
        if response.status_code == 200:
            colored_message("✅ BGM令牌验证成功", Fore.GREEN)
            return True
        elif response.status_code == 401:
            colored_message("❌ 无效的BGM令牌", Fore.RED)
            return False
        else:
            colored_message(f"❗ 验证失败（状态码：{response.status_code}）", Fore.RED)
            return False
    except RequestException as e:
        colored_message(f"⚠️ 网络错误：{str(e)}", Fore.RED)
        colored_message("是否跳过验证？(y/n)", Fore.YELLOW)
        return colored_input().lower() in ["y", "yes"]


def validate_komga_access(password):
    """验证Komga账户密码有效性"""
    base_url = config_values.get("KOMGA_BASE_URL")
    email = config_values.get("KOMGA_EMAIL")
    if not all([base_url, email, password]):
        return False
    try:
        colored_message("🔗 正在验证Komga凭据...", Fore.YELLOW)
        api = KomgaApi(base_url, email, password)
        url = f"{base_url}/api/v1/login/set-cookie"
        response = api.r.get(url, auth=(email, password))
        if response.status_code == 204:
            colored_message("✅ Komga账户验证成功", Fore.GREEN)
            return True
        else:
            colored_message("❌ 无效的Komga账户凭证", Fore.RED)
            return False
    except Exception as e:
        colored_message(f"⚠️ 验证失败: {str(e)}", Fore.RED)
        return False


def configurate_komga_libraries(base_url, email, password):
    """获取Komga库列表并交互选择"""
    try:
        colored_message("🔗 正在获取Komga库列表...", Fore.YELLOW)
        api = KomgaApi(base_url, email, password)
        libraries = api.list_libraries()
        if not libraries:
            colored_message("❌ 未找到任何库", Fore.RED)
            return []
        colored_message(f"✅ 找到 {len(libraries)} 个库", Fore.GREEN)
        selected = []
        for lib in libraries:
            while True:
                choice = colored_input(
                    f"包含库 '{lib['name']}' (ID: {lib['id']})? (y/n): ", Fore.CYAN
                ).lower()
                if choice in ["y", "yes"]:
                    is_novel = colored_input(
                        f"该库是否为小说专用? (y/n): ", Fore.CYAN
                    ).lower() in ["y", "yes"]
                    selected.append({"LIBRARY": lib["id"], "IS_NOVEL_ONLY": is_novel})
                    break
                elif choice in ["n", "no"]:
                    break
                else:
                    colored_message("请输入 y 或 n", Fore.RED)
        return selected
    except Exception as e:
        colored_message(f"⚠️ 获取失败: {str(e)}", Fore.RED)
        return None


def configurate_komga_collections(base_url, email, password):
    """获取Komga收藏列表并交互选择"""
    try:
        colored_message("🔗 正在获取Komga收藏列表...", Fore.YELLOW)
        api = KomgaApi(base_url, email, password)
        collections = api.list_collections()
        if not collections:
            colored_message("❌ 未找到任何收藏集", Fore.RED)
            return []
        colored_message(f"✅ 找到 {len(collections)} 个收藏集", Fore.GREEN)
        selected = []
        for coll in collections:
            while True:
                choice = colored_input(
                    f"包含收藏 '{coll['name']}' (ID: {coll['id']})? (y/n): ", Fore.CYAN
                ).lower()
                if choice in ["y", "yes"]:
                    is_novel = colored_input(
                        f"该收藏是否为小说专用? (y/n): ", Fore.CYAN
                    ).lower() in ["y", "yes"]
                    selected.append(
                        {"COLLECTION": coll["id"], "IS_NOVEL_ONLY": is_novel}
                    )
                    break
                elif choice in ["n", "no"]:
                    break
                else:
                    colored_message("请输入 y 或 n", Fore.RED)
        return selected
    except Exception as e:
        colored_message(f"⚠️ 获取失败: {str(e)}", Fore.RED)
        return None


def manual_input_id_list(name):
    """手动输入 ID 列表（支持库或收藏）"""
    kind = "库" if "LIBRARY" in name else "收藏集"
    colored_message(f"📌 手动输入 {kind} ID 列表（逗号分隔）", Fore.YELLOW)
    user_input = colored_input(
        f"请输入 {kind} ID（如 lib-xxx, coll-yyy）: ", Fore.CYAN
    ).strip()
    if not user_input:
        return []
    ids = [i.strip() for i in user_input.split(",") if i.strip()]
    result = []
    for idx, item_id in enumerate(ids):
        is_novel = colored_input(
            f"ID '{item_id}' 是否为小说专用? (y/n): ", Fore.CYAN
        ).lower() in ["y", "yes"]
        field = "LIBRARY" if "LIBRARY" in name else "COLLECTION"
        result.append({field: item_id, "IS_NOVEL_ONLY": is_novel})
    return result


def parse_template(template_file=TEMPLATE_FILE):
    """解析模板文件，提取配置项"""
    config_schema = []
    current_metadata = {}
    with open(template_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("# @@"):
                match = re.match(r"# @@(\w+):\s*(.*)", line)
                if match:
                    key, value = match.groups()
                    current_metadata[key] = value.strip()
            elif line and "=" in line:
                if "name" not in current_metadata:
                    current_metadata = {}
                    continue
                name = current_metadata.get("name")
                prompt = current_metadata.get("prompt", "")
                var_type = current_metadata.get("type", "string")
                required = current_metadata.get("required", "False").lower() == "true"
                validator = current_metadata.get("validator")
                info = current_metadata.get("info", "")
                version = current_metadata.get("version", "")
                allowed_values = current_metadata.get("allowed_values")
                _, value_part = line.split("=", 1)
                try:
                    default = ast.literal_eval(value_part.strip())
                except:
                    default = value_part.strip()
                schema_item = {
                    "name": name,
                    "prompt": prompt,
                    "default": default,
                    "type": var_type,
                    "required": required,
                    "validator": validator,
                    "info": info,
                    "version": version,
                }
                if allowed_values:
                    schema_item["allowed_values"] = [
                        d.strip() for d in allowed_values.split(",")
                    ]
                config_schema.append(schema_item)
                current_metadata = {}
    return config_schema


def display_config_preview(config_values):
    """配置预览功能"""
    colored_message("\n🔍 配置文件预览：", Fore.YELLOW)
    print("=" * 50)
    for key, value in config_values.items():
        value_str = json.dumps(value) if isinstance(value, list) else str(value)
        print(f"{Fore.MAGENTA}{key}: {Style.RESET_ALL}{value_str}")
    print("=" * 50)
    while True:
        confirm = colored_input("确认配置？(y/n): ", Fore.GREEN).lower()
        if confirm in ["y", "yes"]:
            return True
        elif confirm in ["n", "no"]:
            modify = colored_input("修改哪个配置项（输入名称或q取消）: ", Fore.CYAN)
            if modify.lower() == "q":
                return True
            elif modify in config_values:
                return modify
            else:
                colored_message("❗ 无效的配置项名称", Fore.RED)
        else:
            colored_message("❗ 请输入 y 或 n", Fore.RED)


def colored_input(prompt, color=Fore.CYAN):
    return input(f"{color}{prompt}{Style.RESET_ALL}")


def colored_message(message, color=Fore.WHITE):
    print(f"{color}{message}{Style.RESET_ALL}")


def masked_input(prompt, default=None, mask="*"):
    print(
        f"{Fore.BLUE}❓ {prompt} (默认: {'*' * len(default) if default else ''}){Style.RESET_ALL}"
    )
    user_input = getpass.getpass("").strip()
    return user_input if user_input else default


def get_validated_template_input(
    prompt, default, var_type, required=False, allowed_values=None
):
    while True:
        if var_type == "password":
            user_input = masked_input(prompt, default=default if default else None)
        else:
            if var_type == "boolean":
                prompt += " (True/False)"
            user_input = colored_input(
                f"❓ {prompt} (默认: {default}): ", Fore.BLUE
            ).strip()

        if not user_input:
            if required:
                colored_message("❗ 此项为必填项，请输入有效值", Fore.RED)
                continue
            return default

        try:
            if var_type == "boolean":
                if user_input.lower() in ["yes", "y", "true"]:
                    return True
                elif user_input.lower() in ["no", "n", "false"]:
                    return False
                else:
                    raise ValueError("请输入 yes/y 或 no/n")
            elif var_type == "integer":
                return int(user_input)
            elif var_type == "email":
                if validate_email(user_input):
                    return user_input
                else:
                    raise ValueError("邮箱格式不正确")
            elif var_type == "url":
                if validate_url(user_input):
                    return user_input
                else:
                    raise ValueError("URL必须以http://或https://开头")
            elif allowed_values:
                if user_input in allowed_values:
                    return user_input
                else:
                    raise ValueError(f"请输入允许的值之一: {', '.join(allowed_values)}")
            elif var_type == "password":
                return user_input if user_input else default
            else:
                return user_input
        except ValueError as e:
            colored_message(f"❌ 输入错误: {e}", Fore.RED)


def is_mounted_config_file(filepath):
    mounted_dirs = ["/config", "/data", "/app/config", "/mnt", "/host"]
    try:
        dirname = os.path.dirname(os.path.abspath(filepath))
        normalized_dir = os.path.normpath(dirname)
        if any(normalized_dir.startswith(mounted) for mounted in mounted_dirs):
            return True
        stat_file = os.stat(filepath)
        stat_root = os.stat("/")
        if stat_file.st_dev != stat_root.st_dev:
            return True
        test_file = filepath + ".test"
        with open(test_file, "w") as f:
            f.write("test")
        os.remove(test_file)
        return False
    except (OSError, IOError):
        return True
    except Exception:
        return False


def should_auto_apply_config():
    if not os.path.exists(PRESENT_FILE):
        return True
    try:
        if is_mounted_config_file(PRESENT_FILE):
            colored_message(
                f"⚠️  检测到 {PRESENT_FILE} 可能被挂载为卷(Docker Volume)", Fore.YELLOW
            )
            colored_message(
                "💡 建议：在宿主机上手动替换配置文件以避免冲突", Fore.YELLOW
            )
            confirm = colored_input("是否仍要强制覆盖？(y/n): ", Fore.RED).lower()
            return confirm in ["y", "yes"]
        else:
            colored_message(f"📁 {PRESENT_FILE} 位于容器本地文件系统", Fore.CYAN)
            colored_message("✅ 允许自动覆盖", Fore.GREEN)
            return True
    except Exception as e:
        colored_message(f"⚠️  安全起见，跳过自动覆盖(检测异常: {e}) ", Fore.YELLOW)
        return False


config_values = {}


def start_config_generate():
    colored_message("🎮 欢迎使用交互式配置生成器", Fore.GREEN)
    colored_message("🔍 正在解析模板文件...", Fore.YELLOW)

    try:
        with open(TEMPLATE_FILE, "r", encoding="utf-8") as f:
            template_lines = f.readlines()
    except FileNotFoundError:
        colored_message(f"❌ 找不到模板文件: {TEMPLATE_FILE}", Fore.RED)
        return
    except Exception as e:
        colored_message(f"❌ 读取模板文件失败: {str(e)}", Fore.RED)
        return

    try:
        config_schema = parse_template()
        colored_message(f"✅ 已识别 {len(config_schema)} 个配置项", Fore.GREEN)
    except Exception as e:
        colored_message(f"❌ 模板解析失败: {str(e)}", Fore.RED)
        return

    global config_values
    config_values = {}

    for item in config_schema:
        while True:
            if item.get("info"):
                colored_message(f"ℹ️ {item['info']}", Fore.BLUE)

            # 特殊处理：KOMGA_LIBRARY_LIST
            if item["name"] == "KOMGA_LIBRARY_LIST":
                has_creds = all(
                    config_values.get(k)
                    for k in ["KOMGA_BASE_URL", "KOMGA_EMAIL", "KOMGA_EMAIL_PASSWORD"]
                )
                if has_creds:
                    choice = colored_input(
                        f"💡 是否从服务器获取库列表？(y/n, 默认: n): ", Fore.CYAN
                    ).lower()
                    if choice in ["y", "yes"]:
                        libs = configurate_komga_libraries(
                            config_values["KOMGA_BASE_URL"],
                            config_values["KOMGA_EMAIL"],
                            config_values["KOMGA_EMAIL_PASSWORD"],
                        )
                        if libs is not None:
                            config_values["KOMGA_LIBRARY_LIST"] = libs
                            colored_message("✅ 已设置 KOMGA_LIBRARY_LIST", Fore.GREEN)
                            break
                # 否则或用户选择否 → 手动输入
                config_values["KOMGA_LIBRARY_LIST"] = manual_input_id_list(
                    "KOMGA_LIBRARY_LIST"
                )
                colored_message("✅ 已手动设置 KOMGA_LIBRARY_LIST", Fore.GREEN)
                break

            # 特殊处理：KOMGA_COLLECTION_LIST
            elif item["name"] == "KOMGA_COLLECTION_LIST":
                has_creds = all(
                    config_values.get(k)
                    for k in ["KOMGA_BASE_URL", "KOMGA_EMAIL", "KOMGA_EMAIL_PASSWORD"]
                )
                if has_creds:
                    choice = colored_input(
                        f"💡 是否从服务器获取收藏列表？(y/n, 默认: n): ", Fore.CYAN
                    ).lower()
                    if choice in ["y", "yes"]:
                        colls = configurate_komga_collections(
                            config_values["KOMGA_BASE_URL"],
                            config_values["KOMGA_EMAIL"],
                            config_values["KOMGA_EMAIL_PASSWORD"],
                        )
                        if colls is not None:
                            config_values["KOMGA_COLLECTION_LIST"] = colls
                            colored_message(
                                "✅ 已设置 KOMGA_COLLECTION_LIST", Fore.GREEN
                            )
                            break
                config_values["KOMGA_COLLECTION_LIST"] = manual_input_id_list(
                    "KOMGA_COLLECTION_LIST"
                )
                colored_message("✅ 已手动设置 KOMGA_COLLECTION_LIST", Fore.GREEN)
                break

            # 通用配置项处理
            current_value = get_validated_template_input(
                item["prompt"],
                item["default"],
                item.get("type", "string"),
                item.get("required", False),
                item.get("allowed_values"),
            )

            validator_name = item.get("validator")
            if validator_name and current_value != item["default"]:
                if validator_name in globals() and callable(globals()[validator_name]):
                    try:
                        is_valid = globals()[validator_name](current_value)
                        if not is_valid:
                            colored_message("❌ 验证失败", Fore.RED)
                            confirm = colored_input(
                                "是否跳过验证继续？(y/n): ", Fore.YELLOW
                            ).lower()
                            if confirm not in ["y", "yes"]:
                                continue
                    except Exception as e:
                        colored_message(f"❗ 验证器执行错误: {str(e)}", Fore.RED)
                        confirm = colored_input(
                            "是否跳过验证继续？(y/n): ", Fore.YELLOW
                        ).lower()
                        if confirm not in ["y", "yes"]:
                            continue

            config_values[item["name"]] = current_value
            if item.get("type") == "password":
                colored_message(
                    f"✅ {Fore.MAGENTA}{item['name']}{Style.RESET_ALL} 已设置",
                    Fore.GREEN,
                )
            else:
                colored_message(
                    f"✅ {Fore.MAGENTA}{item['name']}{Style.RESET_ALL} 被设置为: {current_value}",
                    Fore.GREEN,
                )
            break

    # === 配置预览 ===
    preview_result = display_config_preview(config_values)
    if preview_result is True:
        colored_message("\nℹ️ 非交互式配置项将以默认值被添加", Fore.BLUE)
        colored_message("\n📦 正在生成配置文件...", Fore.YELLOW)
        try:
            with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                for line in template_lines:
                    stripped_line = line.strip()
                    if stripped_line.startswith("#"):
                        continue
                    match = re.match(r"^([A-Za-z0-9_]+)\s*=\s*(.+)$", stripped_line)
                    if match:
                        name = match.group(1)
                        if name in config_values:
                            value = config_values[name]
                            if isinstance(value, str):
                                f.write(f"{name} = '{value}'\n")
                            elif isinstance(value, bool):
                                f.write(f"{name} = {value}\n")
                            elif isinstance(value, int):
                                f.write(f"{name} = {value}\n")
                            elif isinstance(value, list):
                                f.write(f"{name} = {value}\n")
                            else:
                                f.write(f"{name} = '{value}'\n")
                            continue
                    f.write(line)
            colored_message(f"🎉 配置文件生成成功！路径: {OUTPUT_FILE}", Fore.GREEN)
        except Exception as e:
            colored_message(f"❌ 写入生成文件失败: {str(e)}", Fore.RED)
            return
    elif isinstance(preview_result, str):
        colored_message(f"🔄 请重新运行以修改 '{preview_result}'", Fore.YELLOW)
        return
    else:
        colored_message("❌ 交互式配置生成已被取消", Fore.RED)
        return

    # === 自动应用到 config.py ===
    if os.path.exists(PRESENT_FILE):
        if should_auto_apply_config():
            try:
                import shutil

                shutil.copy(OUTPUT_FILE, PRESENT_FILE)
                colored_message(f"🎉 已成功更新配置文件: {PRESENT_FILE}", Fore.GREEN)
            except Exception as e:
                colored_message(f"❌ 覆盖失败: {str(e)}", Fore.RED)
        else:
            colored_message(f"📄 生成的配置已保存至: {OUTPUT_FILE}", Fore.YELLOW)
            colored_message(f"📌 请手动复制到宿主机以更新 {PRESENT_FILE}", Fore.YELLOW)
    else:
        try:
            import shutil

            shutil.copy(OUTPUT_FILE, PRESENT_FILE)
            colored_message(f"🎉 配置文件已创建: {PRESENT_FILE}", Fore.GREEN)
        except Exception as e:
            colored_message(f"❌ 创建失败: {str(e)}", Fore.RED)
            colored_message(
                f"📌 请手动复制 {OUTPUT_FILE} 到 {PRESENT_FILE}", Fore.YELLOW
            )


if __name__ == "__main__":
    start_config_generate()
