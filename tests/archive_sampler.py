import json
import random
import os
from config.config import ARCHIVE_FILES_DIR


def sample_jsonl():
    """从JSONLINE文件中流式地随机采样 type=1 的数据"""
    # 采样数量
    required_count = 100
    # 目标数据
    target_file = 'subject.jsonlines'

    # input_path = os.path.join('..', ARCHIVE_FILES_DIR, target_file)
    input_path = os.path.join(ARCHIVE_FILES_DIR, target_file)
    output_path = f'sampled_{target_file}.py'
    buffer = []

    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    data = json.loads(line.strip())
                    if data.get('type') == 1:
                        buffer.append(data)
                except json.JSONDecodeError:
                    continue

        if len(buffer) < required_count:
            print(f"警告: 仅找到{len(buffer)}条符合条件的数据")
            sampled_data = buffer
        else:
            sampled_data = random.sample(buffer, required_count)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"test_data = {repr(sampled_data)}")

        print(f"采样完成, 共保存{len(sampled_data)}条数据到{output_path}")

    except FileNotFoundError:
        print(f"错误: 输入文件{input_path}未找到")
    except Exception as e:
        print(f"处理过程中发生错误: {str(e)}")


if __name__ == "__main__":
    sample_jsonl()
