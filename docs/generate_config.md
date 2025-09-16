# 交互式配置生成

`config.template.py`配置模板文件包含多个描述行，此处以配置项`KOMGA_BASE_URL`为例进行说明:

  ```python
  # @@name: KOMGA_BASE_URL
  # @@prompt: KOMGA访问地址
  # @@type: url
  # @@required: True
  # @@validator: validate_url
  # @@info:
  KOMGA_BASE_URL = "http://IP:PORT"
  ```

- `# @@name` 表示该配置项的显示名称 `KOMGA_BASE_URL`。
- `# @@prompt` 表示该配置项的输入提示。
- `# @@type` 表示该配置项被视为何种数据类型，其可选值为 `password`, `string`, `url`, `boolean`, `integer`, 该例中使用 `url`。
- `# @@validator` 表示该配置项应调用哪个验证器来验证有效性, 其可选值为`validate_email`，`validate_url`，`validate_bangumi_token` 和 `validate_komga_access`, 该例中使用 `validate_url`。
- `# @@required` 表示该配置项是否为必填项，其可选值为 `True` 和 `False`，该例中使用 `True`。
- `# @@info` 表示该配置项所显示的解释文本。
- `KOMGA_BASE_URL = "http://IP:PORT"` 表示配置项 `KOMGA_BASE_URL` 的默认值为 `http://IP:PORT`

## 命令行交互式配置生成器

- 命令行交互式配置生成器将读取 `config` 目录下的配置模板文件 `config.template.py`, 文件中附有 `# @@` 的配置项将允许用户进行交互式配置, 而无需手动编辑配置文件; 而其他配置项则跳过交互式配置，以默认值直接写入配置生成文件 `config.generated.py`。命令行交互式配置生成器成功生成 `config.generated.py` 文件后，将会用配置生成文件 `config.generated.py` 覆盖 `config.py`，因此请在启动交互式配置生成流程前备份已有的配置文件，避免错误覆盖。

## 网页配置生成器

在[命令行交互式配置生成器](./generate_config.md#命令行交互式配置生成器)的基础上提供网页配置
