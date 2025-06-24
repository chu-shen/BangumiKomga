# configuration_generator.py (增强版)
import re
from colorama import Fore, Style, init
import getpass
import requests

init()


def masked_input(prompt, default=None, mask="*"):
    """带掩码的密码输入"""
    print(f"{Fore.BLUE}❓ {prompt} (默认: {'*' * len(default) if default else ''}){Style.RESET_ALL}")
    user_input = getpass.getpass("").strip()
    return user_input if user_input else default


def validate_email(email):
    """基础邮箱格式验证"""
    return re.match(r"[^@]+@[^@]+\.[^@]+", email) is not None


def validate_url(url):
    """基础URL格式验证"""
    return url.startswith(('http://', 'https://'))


def color_input(prompt, color=Fore.CYAN):
    return input(f"{color}{prompt}{Style.RESET_ALL}")


def colored_message(message, color=Fore.WHITE):
    print(f"{color}{message}{Style.RESET_ALL}")


def validate_bangumi_token(token):
    """验证BGM访问令牌"""
    headers = {
        "Accept": "application/json",
        "User-Agent": "chu-shen/BangumiKomga (https://github.com/chu-shen/BangumiKomga)",
        "Authorization": f"Bearer {token}"
    }

    try:
        colored_message("🔗 正在验证BGM令牌...", Fore.YELLOW)
        response = requests.get(
            "https://api.bgm.tv/oauth/test/token",
            headers=headers
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
    except requests.RequestException as e:
        colored_message(f"⚠️ 网络错误：{str(e)}", Fore.RED)
        colored_message("是否跳过验证？(y/n)", Fore.YELLOW)
        return color_input().lower() in ['y', 'yes']


def get_komga_libraries(base_url, email, password):
    """获取Komga库列表"""
    auth = (email, password)

    try:
        colored_message("🔗 正在获取Komga库列表...", Fore.YELLOW)
        response = requests.get(
            f"{base_url.rstrip('/')}/api/v1/libraries",
            auth=auth
        )

        if response.status_code == 200:
            libraries = response.json()
            colored_message(f"✅ 找到 {len(libraries)} 个库", Fore.GREEN)

            selected_libraries = []
            for lib in libraries:
                while True:
                    choice = color_input(
                        f"是否包含库 '{lib['name']}' (ID: {lib['id']})? (y/n): ",
                        Fore.CYAN
                    ).lower()
                    if choice in ['y', 'yes']:
                        selected_libraries.append(lib['id'])
                        break
                    elif choice in ['n', 'no']:
                        break
                    else:
                        colored_message("请输入 y 或 n", Fore.RED)
            return selected_libraries
        else:
            colored_message(f"❌ 获取失败（状态码：{response.status_code}）", Fore.RED)
            return []
    except requests.RequestException as e:
        colored_message(f"⚠️ 网络错误：{str(e)}", Fore.RED)
        colored_message("是否跳过库获取？(y/n)", Fore.YELLOW)
        return [] if color_input().lower() in ['y', 'yes'] else None


def get_validated_input(prompt, default, var_type, required=False, allowed_values=None):
    """带验证的用户输入"""
    while True:
        user_input = color_input(f"❓ {prompt} (默认值: {default}): ", Fore.BLUE)

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
                    raise ValueError(
                        f"{Fore.RED}请输入 yes/y 或 no/n{Style.RESET_ALL}")
            # 密码输入函数（带掩码）
            if var_type == "password":
                return masked_input(prompt, default)
            elif var_type == "integer":
                return int(user_input)

            elif var_type == "email":
                if validate_email(user_input):
                    return user_input
                else:
                    raise ValueError(f"{Fore.RED}邮箱格式不正确{Style.RESET_ALL}")

            elif var_type == "url":
                if validate_url(user_input):
                    return user_input
                else:
                    raise ValueError(
                        f"{Fore.RED}URL必须以http://或https://开头{Style.RESET_ALL}")

            elif allowed_values:
                if user_input in allowed_values:
                    return user_input
                else:
                    raise ValueError(
                        f"{Fore.RED}请输入允许的值之一: {', '.join(allowed_values)}{Style.RESET_ALL}")

            else:
                return user_input

        except ValueError as e:
            print(f"{Fore.RED}❌ 输入错误: {e}{Style.RESET_ALL}")


def display_config_preview(config_values):
    """配置预览功能"""
    colored_message("\n🔍 配置文件预览：", Fore.YELLOW)
    print("=" * 50)
    for key, value in config_values.items():
        if isinstance(value, list):
            value_str = ", ".join(value)
        elif isinstance(value, bool):
            value_str = str(value)
        else:
            value_str = value
        print(f"{Fore.MAGENTA}{key}: {Style.RESET_ALL}{value_str}")
    print("=" * 50)

    while True:
        confirm = color_input("确认配置？(y/n): ", Fore.GREEN).lower()
        if confirm in ['y', 'yes']:
            return True
        elif confirm in ['n', 'no']:
            modify = color_input("修改哪个配置项（输入名称或q取消）: ", Fore.CYAN)
            if modify.lower() == 'q':
                return True
            elif modify in config_values:
                return modify  # 返回需要修改的配置项名称
            else:
                colored_message("❗ 无效的配置项名称", Fore.RED)
        else:
            colored_message("❗ 请输入 y 或 n", Fore.RED)


def main():
    # ...原有初始化代码保持不变...

    # 配置项定义
    config_schema = [
        {
            "name": "BANGUMI_ACCESS_TOKEN",
            "prompt": "BGM访问令牌(获取地址: https://next.bgm.tv/demo/access-token)",
            "default": "gruUsn***************************SUSSn",
            "type": "password",
            "required": True
        },
        {
            "name": "KOMGA_BASE_URL",
            "prompt": "Komga基础URL(示例: http://localhost:8080)",
            "default": "http://IP:PORT",
            "type": "url",
            "required": True
        },
        {
            "name": "KOMGA_EMAIL",
            "prompt": "Komga登录邮箱",
            "default": "email",
            "type": "email",
            "required": True
        },
        {
            "name": "KOMGA_EMAIL_PASSWORD",
            "prompt": "Komga邮箱密码",
            "default": "password",
            "type": "password",
            "required": True
        },
        {
            "name": "KOMGA_LIBRARY_LIST",
            "prompt": "Komga库ID列表(逗号分隔)",
            "default": "[]",
            "type": "list"
        },
        {
            "name": "KOMGA_COLLECTION_LIST",
            "prompt": "Komga收藏夹ID列表(逗号分隔)",
            "default": "[]",
            "type": "list"
        },
        {
            "name": "USE_BANGUMI_ARCHIVE",
            "prompt": "使用离线元数据",
            "default": False,
            "type": "boolean"
        },
        {
            "name": "ARCHIVE_FILES_DIR",
            "prompt": "离线数据存储目录",
            "default": "./archivedata/",
            "type": "string"
        },
        {
            "name": "BANGUMI_KOMGA_SERVICE_TYPE",
            "prompt": "服务运行模式",
            "default": "once",
            "type": "string",
            "allowed_values": ["once", "poll", "sse"]
        },
        {
            "name": "BANGUMI_KOMGA_SERVICE_POLL_INTERVAL",
            "prompt": "轮询间隔（秒）",
            "default": 20,
            "type": "integer"
        },
        {
            "name": "BANGUMI_KOMGA_SERVICE_POLL_REFRESH_ALL_METADATA_INTERVAL",
            "prompt": "全量刷新间隔（次数）",
            "default": 10000,
            "type": "integer"
        },
    ]

    config_values = {}

    while True:
        print("\n🔧 开始配置：")
        for item in config_schema:
            current_value = get_validated_input(
                item["prompt"],
                item["default"],
                item.get("type", "string"),
                item.get("required", False),
                item.get("allowed_values")
            )
            config_values[item["name"]] = current_value
            print(f"✅ 设置 {item['name']} = {current_value}\n")
        # 添加预览环节
        preview_result = display_config_preview(config_values)
        if isinstance(preview_result, str):
            # 修改指定配置项
            current_value = get_validated_input(
                next(item["prompt"]
                     for item in config_schema if item["name"] == preview_result),
                config_values[preview_result],
                next(item["type"]
                     for item in config_schema if item["name"] == preview_result),
                next(item.get("required", False)
                     for item in config_schema if item["name"] == preview_result),
                next((item.get("allowed_values")
                     for item in config_schema if item["name"] == preview_result), None)
            )
            config_values[preview_result] = current_value
        elif preview_result:
            break  # 确认配置

        print("\n📦 正在生成配置文件...")
        with open("config.py", "w", encoding="utf-8") as f:
            for key, value in config_values.items():
                if isinstance(value, str):
                    f.write(f"{key} = '{value}'\n")
                elif isinstance(value, bool):
                    f.write(f"{key} = {value}\n")
                elif isinstance(value, int):
                    f.write(f"{key} = {value}\n")
                elif isinstance(value, list):
                    f.write(f"{key} = {value}\n")
                else:
                    f.write(f"{key} = '{value}'\n")

        print("\n🎉 配置文件生成成功！")
        print("📄 文件路径: ./config.py")
        print("💡 提示：请检查配置内容，确保符合您的需求")


if __name__ == "__main__":
    main()
