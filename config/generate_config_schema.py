import json
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))
from configuration_generator import parse_template


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_FILE = os.path.join(PROJECT_ROOT, "web", "config_schema.json")
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(parse_template(), f, indent=2, ensure_ascii=False)
print("配置 schema 已生成到：", OUTPUT_FILE)
#TODO 完整的配置 schema 生成脚本
#TODO 上传本地配置