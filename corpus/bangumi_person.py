import json
import re

# 读取文件 person.jsonlines
with open('person.jsonlines', 'r', encoding='utf-8') as file:
    # 创建新文件 bangumi_person.txt
    with open('bangumi_person.txt', 'w', encoding='utf-8') as names_file:
        for line in file:
            # 转换 JSON 对象
            data = json.loads(line)
            # 提取名称
            name = data.get('name')
            if name:
                # 写入新文件
                names_file.write(name + '\n')
                
            # 提取简体中文名
            infobox = data.get('infobox')
            chinese_name = re.search(
                '(?<=简体中文名\= ).+?(?=\\r\\n)', infobox)
            if chinese_name is not None:
                # 写入新文件
                names_file.write(chinese_name.group() + '\n')
