# configuration_generator.py
import re
import ast
import os
import getpass
import json
import requests
from colorama import Fore, Style, init
from requests.exceptions import RequestException
from api.komga_api import KomgaApi

# TODO：统一初始化 KomgaApi 复用连接

# 初始化 colorama（Windows 必需）
init()

# 全局常量
MAX_RETRIES = 3
TIMEOUT = 20
USER_AGENT = "chu-shen/BangumiKomga (https://github.com/chu-shen/BangumiKomga)"
TEMPLATE_FILE = os.path.join(os.getcwd(), 'config', 'config.template.py')
OUTPUT_FILE = os.path.join(os.getcwd(), 'config', 'config.generated.py')


def validate_email(email):
    """邮箱格式验证"""
    return re.match(r"[^@]+@[^@]+\.[^@]+", email) is not None


def validate_url(url):
    """URL格式验证"""
    return url.startswith(('http://', 'https://'))


def validate_bangumi_token(token):
    """验证BGM访问令牌有效性"""
    headers = {
        "User-Agent": USER_AGENT,
        "Authorization": f"Bearer {token}"
    }
    try:
        colored_message("🔗 正在验证BGM令牌...", Fore.YELLOW)
        session = requests.Session()
        # 使用工口漫画<求愛エトランゼ> https://bangumi.tv/subject/278395 进行测试
        test_URL = 'https://api.bgm.tv/v0/subjects/278395'
        # 剑风传奇 9640
        # test_URL = 'https://api.bgm.tv/v0/subjects/9640'
        response = session.get(
            test_URL,
            headers=headers,
            timeout=TIMEOUT
        )
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
        return colored_input().lower() in ['y', 'yes']


def validate_komga_access(password):
    """验证Komga账户密码有效性"""
    base_url = config_values.get("KOMGA_BASE_URL")
    email = config_values.get("KOMGA_EMAIL")
    if not all([base_url, email, password]):
        return False  # 依赖项未满足时跳过验证
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
    colored_message("🔗 正在获取Komga库列表...", Fore.YELLOW)
    libraries = KomgaApi(base_url, email, password).get_all_libraries()
    try:
        if libraries:
            colored_message(f"✅ 找到 {len(libraries)} 个库", Fore.GREEN)
            selected_libraries = []
            for lib in libraries:
                specific_library = {}
                while True:
                    lib_choice = colored_input(
                        f"是否包含库 '{lib['name']}' (ID: {lib['id']})? (y/n): ", Fore.CYAN).lower()
                    if lib_choice in ['y', 'yes', 'true']:
                        specific_library['LIBRARY'] = lib['id']
                        novel_choice = colored_input(
                            f"库 '{lib['name']}' (ID: {lib['id']})是否为小说库? (y/n): ", Fore.CYAN).lower()
                        if novel_choice in ['y', 'yes', 'true']:
                            specific_library['IS_NOVEL_ONLY'] = True
                        else:
                            specific_library['IS_NOVEL_ONLY'] = False
                        break
                    elif lib_choice in ['n', 'no', 'false']:
                        break
                    else:
                        colored_message("请输入 yes 或 no", Fore.RED)
                if specific_library:
                    selected_libraries.append(specific_library)
            return selected_libraries
        else:
            colored_message(f"❌ Komga 库列表为空或获取失败", Fore.RED)
            return []
    except RequestException as e:
        colored_message(f"⚠️ 网络错误：{str(e)}", Fore.RED)
        colored_message("是否跳过库设置？(y/n)", Fore.YELLOW)
        return [] if colored_input().lower() in ['y', 'yes'] else None


def parse_template():
    """解析模板文件，提取配置项"""
    config_schema = []
    current_metadata = {}

    with open(TEMPLATE_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            # 解析元数据注释
            if line.startswith('# @@'):
                match = re.match(r'# @@(\w+):\s*(.*)', line)
                if match:
                    key, value = match.groups()
                    current_metadata[key] = value.strip()
            # 解析配置项
            elif line and '=' in line:
                if 'name' not in current_metadata:
                    current_metadata = {}
                    continue

                name = current_metadata.get('name')
                prompt = current_metadata.get('prompt', '')
                var_type = current_metadata.get('type', 'string')
                required = current_metadata.get(
                    'required', 'False').lower() == 'true'
                validator = current_metadata.get('validator')
                info = current_metadata.get('info', '')
                dependency = current_metadata.get('dependency')

                # 解析默认值
                _, value_part = line.split('=', 1)
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
                    "info": info
                }
                if dependency:
                    schema_item["dependency"] = [d.strip()
                                                 for d in dependency.split(',')]
                config_schema.append(schema_item)
                current_metadata = {}  # 重置元数据

    return config_schema


def display_config_preview(config_values):
    """配置预览功能"""
    colored_message("\n🔍 配置文件预览：", Fore.YELLOW)
    print("=" * 50)
    for key, value in config_values.items():
        if isinstance(value, list):
            try:
                value_str = json.dumps(value)
            except Exception as e:
                value_str = ", ".join(str(value))
        else:
            value_str = str(value)
        print(f"{Fore.MAGENTA}{key}: {Style.RESET_ALL}{value_str}")
    print("=" * 50)
    while True:
        confirm = colored_input("确认配置？(y/n): ", Fore.GREEN).lower()
        if confirm in ['y', 'yes']:
            return True
        elif confirm in ['n', 'no']:
            modify = colored_input("修改哪个配置项（输入名称或q取消）: ", Fore.CYAN)
            if modify.lower() == 'q':
                return True
            elif modify in config_values:
                return modify
            else:
                colored_message("❗ 无效的配置项名称", Fore.RED)
        else:
            colored_message("❗ 请输入 y 或 n", Fore.RED)


def colored_input(prompt, color=Fore.CYAN):
    """带颜色的输入提示"""
    return input(f"{color}{prompt}{Style.RESET_ALL}")


def colored_message(message, color=Fore.WHITE):
    """带颜色的消息输出"""
    print(f"{color}{message}{Style.RESET_ALL}")


def masked_input(prompt, default=None, mask="*"):
    """带掩码的密码输入"""
    print(f"{Fore.BLUE}❓ {prompt} (默认: {'*' * len(default) if default else ''}){Style.RESET_ALL}")
    user_input = getpass.getpass("").strip()
    return user_input if user_input else default


def get_validated_template_input(prompt, default, var_type, required=False, allowed_values=None):
    """带验证的用户输入"""
    while True:
        # 显示提示信息
        if var_type == "password":
            user_input = masked_input(
                prompt, default=default if default else None)
        else:
            if var_type == "boolean":
                prompt += " (True/False)"
            user_input = colored_input(
                f"❓ {prompt} (默认: {default}): ", Fore.BLUE).strip()

        if not user_input:
            if required:
                colored_message("❗ 此项为必填项，请输入有效值", Fore.RED)
                continue
            return default

        try:
            if var_type == "boolean":
                if user_input.lower() in ['yes', 'y', 'true']:
                    return True
                elif user_input.lower() in ['no', 'n', 'false']:
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


config_values = {}


def main():
    colored_message("🎮 欢迎使用交互式配置生成器", Fore.GREEN)
    colored_message("🔍 正在解析模板文件...", Fore.YELLOW)

    # 读取模板文件内容
    with open(TEMPLATE_FILE, "r", encoding="utf-8") as f:
        template_lines = f.readlines()

    try:
        config_schema = parse_template()
        colored_message(f"✅ 已识别 {len(config_schema)} 个配置项", Fore.GREEN)
    except Exception as e:
        colored_message(f"❌ 模板解析失败: {str(e)}", Fore.RED)
        return

    # 处理配置项
    for item in config_schema:

        # 获取当前项值
        while True:
            # 显示提示信息
            if item.get("info"):
                colored_message(f"ℹ️ {item['info']}", Fore.BLUE)

            current_value = get_validated_template_input(
                item["prompt"],
                item["default"],
                item.get("type", "string"),
                item.get("required", False),
                item.get("allowed_values")
            )
            # 处理Komga库获取
            if item["name"] == 'KOMGA_LIBRARY_LIST':
                komga_libraries = None
                if "KOMGA_BASE_URL" in config_values and "KOMGA_EMAIL" in config_values and "KOMGA_EMAIL_PASSWORD" in config_values:
                    komga_libraries = configurate_komga_libraries(
                        config_values["KOMGA_BASE_URL"],
                        config_values["KOMGA_EMAIL"],
                        config_values["KOMGA_EMAIL_PASSWORD"]
                    )
                if komga_libraries is not None:
                    config_values["KOMGA_LIBRARY_LIST"] = komga_libraries
                    break
            # 转交给验证器处理
            validator_name = item.get("validator")
            if validator_name and current_value != item["default"]:
                if validator_name in globals() and callable(globals()[validator_name]):
                    validator_func = globals()[validator_name]
                    is_valid = False
                    try:
                        # 验证器返回结果
                        is_valid = validator_func(current_value)
                    except Exception as e:
                        colored_message(f"❗ 验证器错误: {str(e)}", Fore.RED)

                    if not is_valid:
                        colored_message("验证失败", Fore.RED)
                        # colored_message("是否跳过验证继续？(y/n)", Fore.YELLOW)
                        confirm = colored_input("是否跳过验证继续？(y/n):").lower()
                        if confirm not in ['y', 'yes']:
                            continue  # 重新输入
                        else:
                            break

            config_values[item["name"]] = current_value
            if item.get("type", "string") == 'password':
                colored_message(
                    f"✅ {Fore.MAGENTA}{item['name']}{Style.RESET_ALL} 已设置")
            else:
                colored_message(
                    f"✅ {Fore.MAGENTA}{item['name']}{Style.RESET_ALL} 被设置为: {current_value}", Fore.GREEN)
            break

    # 配置预览与确认
    if display_config_preview(config_values):
        colored_message("\nℹ️ 非交互式配置项将以默认值被添加", Fore.BLUE)
        colored_message("\n📦 正在生成配置文件...", Fore.YELLOW)
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            for line in template_lines:
                stripped_line = line.strip()
                # 跳过所有以 # 开头的注释行（包括空行和纯注释行）
                if stripped_line.startswith('#'):
                    continue

                # 处理配置项替换
                match = re.match(
                    r'^([A-Za-z0-9_]+)\s*=\s*(.+)$', stripped_line)
                if match:
                    name = match.group(1)
                    if name in config_values:
                        value = config_values[name]
                        # 可配置的写入格式
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

                # 保留非交互式配置项的原始行(如 FUZZ_SCORE_THRESHOLD = 80)
                f.write(line)
        colored_message(f"🎉 配置文件生成成功！路径: {OUTPUT_FILE} 🎉", Fore.GREEN)
    else:
        colored_message("❌ 交互式配置生成已被取消", Fore.RED)


if __name__ == "__main__":
    main()
