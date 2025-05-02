# Bangumi metadata scraper for Komga

- [Bangumi metadata scraper for Komga](#bangumi-metadata-scraper-for-komga)
  - [简介](#简介)
  - [功能](#功能)
    - [已完成](#已完成)
    - [TODO](#todo)
  - [先决条件](#先决条件)
  - [快速开始](#快速开始)
  - [Bangumi 配置（可选）](#bangumi-配置可选)
  - [消息通知（可选）](#消息通知可选)
  - [创建失败收藏（可选）](#创建失败收藏可选)
  - [其他配置说明](#其他配置说明)
  - [为小说添加元数据](#为小说添加元数据)
  - [如何修正错误元数据](#如何修正错误元数据)
  - [同步阅读进度](#同步阅读进度)
  - [命名建议](#命名建议)
  - [Issues \& Pull Requests](#issues--pull-requests)
  - [致谢](#致谢)

> [!WARNING]
>
> 如果 2025 年你并未执行过更新，那你可能需要重新阅读配置说明\
> 新增了一些实用配置，并且部分配置的逻辑存在细微调整

## 简介

该脚本获取您 Komga 实例上可用的漫画列表, 挨个在 [Bangumi](https://bgm.tv/) 上查询, 并按配置获取指定系列的元数据。
然后将这些元数据转换为与 Komga 兼容的格式, 并更新到 Komga 服务器的具体漫画条目中。

![sample](img/sample.jpg)
![detail](img/detail.jpg)

## 功能

### 已完成

- [x] 为失败的系列创建收藏（可选）
- [x] 通知执行结果（可选）
- [x] 漫画系列添加元数据
- [x] 单册漫画添加元数据
- [x] 自动跳过已刷新元数据的条目
- [x] 系列及单册优先使用手动配置的 Bangumi 链接(cbl)
- [x] 配置 Bangumi 登录
- [x] 同步观看进度至 Bangumi
- [x] 可选择处理范围：①所有书籍系列；②指定库的书籍系列；③指定收藏的书籍系列
- [x] ~~区分单册和单话~~👉未匹配的书也会重新排序
- [x] ~~添加同人志~~👉推荐使用[LANraragi](https://github.com/Difegue/LANraragi)
- [x] 可使用 Bangumi 图片替换系列、单册封面
- [x] 排序标题，支持字母导航
- [x] 提高匹配准确率：使用 FUZZ 对 bgm 搜索结果进行过滤和排序
- [x] 使用[bangumi/Archive](https://github.com/bangumi/Archive)离线数据代替联网查询

处理逻辑见[DESIGN](docs/DESIGN.md)

### TODO

- [ ] 限制联网查询频率
- [ ] 更新 Komga 封面时，判断：类型（'GENERATED'）、大小
- [ ] 重构元数据更新范围及覆盖逻辑
- [ ] 增强文件名解析
- [ ] 自动化测试

## 先决条件

- 一个有 admin 权限的 Komga 实例
- 使用 Windows/Linux/MAc 等主流操作系统, 也可在其上使用 Docker
- 如需在 Windows, Linux 或 Mac 上直接执行脚本, 应安装有Python

## 快速开始

> [!WARNING]
>
> Executing this program will result in the loss of old metadata for series and books\
> 执行此程序将导致书籍系列及单册的旧元数据丢失

1. 安装依赖包

    ```shell
    # 准备环境
    pip3 install -r install/requirements.txt

    # 亦可使用 docker compose
    version: '3'
    services:
    bangumikomga:
        image: chu1shen/bangumikomga:main
        container_name: bangumikomga
        volumes:
        - /path/BangumiKomga/config.py:/app/config/config.py   # see step.2
        - /path/BangumiKomga/recordsRefreshed.db:/app/recordsRefreshed.db
        - /path/BangumiKomga/logs:/app/logs
    ```

2. 将 `config/config.template.py` 重命名为 `config/config.py`, 并修改 `KOMGA_BASE_URL`, `KOMGA_EMAIL` 和 `KOMGA_EMAIL_PASSWORD` 以便程序访问你的 Komga 实例(此用户需要有 Komga 元数据修改权限)。

    `KOMGA_LIBRARY_LIST` 处理指定库中的书籍系列。komga界面点击库（对应链接）即可获得，形如：`'0B79XX3NP97K9'`，对应地址：`http://IP:PORT/libraries/0B79XX3NP97K9/series`。填写时以英文引号`''`包裹，英文逗号`,`分割。与`KOMGA_COLLECTION_LIST`不能同时使用

    `KOMGA_COLLECTION_LIST` 处理指定收藏中的书籍系列。komga界面点击收藏（对应链接）即可获得，形如：`'0B79XX3NP97K9'`。填写时以英文引号`''`包裹，英文逗号`,`分割。与`KOMGA_LIBRARY_LIST`不能同时使用

3. 用 `python refreshMetadata.py` 执行脚本, 或者用 `docker start bangumikomga` 启动Docker容器(执行后容器将自动关闭)

> [!TIP]
>
> - 如果漫画系列数量上千，请考虑使用[bangumi/Archive](https://github.com/bangumi/Archive)离线数据代替联网查询
> - 可以搭配工具定时执行，比如[ofelia](https://github.com/mcuadros/ofelia)

## Bangumi 配置（可选）

- `BANGUMI_ACCESS_TOKEN`: 用于读取 NSFW 条目
  - 请**自行**确认账号能否正常访问 NSFW 条目
  - 在 <https://next.bgm.tv/demo/access-token> 创建个人令牌
  - 如果不使用，请设置为`''`

- `USE_BANGUMI_ARCHIVE`: 指定是否优先使用[bangumi/Archive](https://github.com/bangumi/Archive)离线元数据
  - 需搭配`ARCHIVE_FILES_DIR`使用
  - 不含图像数据因此无法离线刷新封面。如果开启`USE_BANGUMI_THUMBNAIL`，则仍需调用 BGM API 才能替换海报
  - 可选值为 `True` 和 `False`

- `ARCHIVE_FILES_DIR`: 指定储存[bangumi/Archive](https://github.com/bangumi/Archive)的本地目录，形如：`./archivedata/`
  - 启用`USE_BANGUMI_ARCHIVE`后，程序会自动从Github下载解压元数据(可能较慢)
  - 离线元数据亦可提前手动解压至该目录中, 另外最好同时创建`archive_update_time.json`并添加日期，内容示例：`{"last_updated": "2025-04-22T21:03:01Z"}`

> [!TIP]
>
> - 如果将`archive_update_time.json`中时间修改为`2099`等较大值，可在很长时间内禁用自动更新

- `USE_BANGUMI_THUMBNAIL`: 设置为`True`且未曾上传过系列海报时，使用 Bangumi 封面替换系列海报
  - 旧海报为 Komga 生成的缩略图，因此还可以通过调整`Komga 服务器设置->缩略图尺寸（默认 300px，超大 1200px）`来获得更清晰的封面
  - `USE_BANGUMI_THUMBNAIL_FOR_BOOK`: 设置为`True`且未曾上传过单册海报时，使用 Bangumi 封面替换单册海报

- `FUZZ_SCORE_THRESHOLD`：满分 100，默认值`80`。用于过滤搜索结果
  - 值越小匹配到错误元数据的可能性越大
  - 值越大匹配失败的可能性越大
  - 默认值`80`并不是一个经验值，有更好的评分请开 issue

## 消息通知（可选）

消息通知支持[Gotify](https://github.com/gotify/server)、Webhook（如：[飞书](https://open.feishu.cn/document/client-docs/bot-v3/add-custom-bot)）、[Healthchecks](https://github.com/healthchecks/healthchecks)（定时任务监控）

- `NOTIF_TYPE_ENABLE`: 启用的消息通知类型

- Gotify
  - `NOTIF_GOTIFY_ENDPOINT`: Gotify base URL
  - `NOTIF_GOTIFY_TOKEN`: Application token

- Webhook
  - `NOTIF_WEBHOOK_ENDPOINT`: URL of the HTTP request. 如飞书中创建自定义机器人时的 webhook 地址

- Healthchecks
  - `NOTIF_HEALTHCHECKS_ENDPOINT`: URL of the HTTP request

## 创建失败收藏（可选）

将`CREATE_FAILED_COLLECTION`配置为`True`，程序会在刷新完成后，将**所有**刷新失败的系列添加到指定收藏（默认名：`FAILED_COLLECTION`）。

> [!TIP]
>
> - 在此收藏中按照[如何修正错误元数据](#如何修正错误元数据)操作即可~~治疗强迫症~~
> - 此收藏采用`手动排序`，因此最新失败的系列在此收藏的最后面

## 其他配置说明

- `RECHECK_FAILED_SERIES`: 重新检查刷新元数据失败的系列
  - 其他情况下建议设置为`False`，可缩短程序运行时间

- `RECHECK_FAILED_BOOKS`: 重新检查刷新元数据失败的书
  - ~~意义不明的参数~~，建议设置为`False`，可缩短程序运行时间
  - 如果刷新书时，bangumi 数据不完整，则可以在数据补充后使用此参数修正此书元数据

- `SORT_TITLE`：设置为`True`时，在刷新元数据后会在系列元数据-排序标题前添加一个首字母用于导航
  - 此为临时方案，详细讨论见：
    - <https://github.com/gotson/komga/discussions/1883>
    - <https://komga.org/docs/guides/edit-metadata#sort-titles>
    - [chu-shen/BangumiKomga#37](https://github.com/chu-shen/BangumiKomga/issues/37)
  - 如果要对此功能启用前的系列进行修改，请在`scripts`目录下手动运行一次`python sortTitleByLetter.py`

## 为小说添加元数据

Komga 并没有区分漫画与小说，建议不同类型使用不同库

`IS_NOVEL_ONLY`：设置为`True`时，将只匹配小说数据；默认设置为`False`，匹配漫画数据

## 如何修正错误元数据

人工修正错误元数据可以使用`cbl(Correct Bangumi Link)`，只需在系列元数据的链接中填入`cbl`和该漫画系列的 bangumi 地址。将强制使用此链接，不再进行刮削。与`RECHECK_FAILED_SERIES`配置无关

![cbl](img/cbl.png)

下面分三种情况说明具体操作：

- 自此系列添加至 komga 后还未运行过此程序：
  - 填入上面提到的信息
  - 正常执行`python refreshMetadata.py`

- 系列元数据更新失败，即「标题」与「排序标题」**一样**：
  - 填入上面提到的信息
  - 如果未填写，也可以尝试使用最新版本重新匹配之前失败的系列
    - 只需将`RECHECK_FAILED_SERIES`配置为`True`，重新匹配失败的系列；将`RECHECK_FAILED_BOOKS`配置为`True`，重新匹配失败的单行本
  - 正常执行`python refreshMetadata.py`

- 系列元数据更新错误，即匹配错误，刮削成其他条目：
  - 填入上面提到的信息
  - 正常执行`python refreshMetadata.py`

## 同步阅读进度

> [!WARNING]
> _注意：当前仅为komga至bangumi单向同步，此功能未维护_

> [!TIP]
> 推荐使用Tachiyomi更新阅读进度👉[Tracking | Tachiyomi](https://tachiyomi.org/help/guides/tracking/#what-is-tracking)

**同步内容：**

- 仅同步卷数，不同步话数

1. 步骤同`刷新元数据`
2. 步骤同`刷新元数据`

    注意：
    - 同步当前获取的**所有系列**的漫画进度（当前有3种范围：所有、仅指定库、仅指定收藏）。**为避免污染时间线，请谨慎操作**
3. `python updateReadProgress.py`

## 命名建议

`[漫画名称][作者][出版社][卷数][其他1][其他2]`

- [漫画名称]：以漫画封面实际名称为准，繁体不必转简体。
- [作者]：作者名字亦以单行本所给名字为准
  - 繁体不转为简体，若有日文假名亦保留，如[島崎讓]、[天王寺きつね]；
  - 若作者为多人，则以`×`或`&`符号连接各作者（**注意：不是英文`x`**），将作画作者列于最后，如[矢立肇×有贺ヒトシ]、[手塚治虫×浦沢直树]、[堀田由美×小畑健]。

- [出版社]：例如[玉皇朝]、[青文]。
- [卷数]：例如[Vol.01-Vol.12]。
- [其他1]、[其他2]：其他信息。例如[完结]、[来源]。

例如：

```txt
[碧蓝之海][井上堅二×吉岡公威][Vol.01-Vol.18]
[相合之物][浅野伦][Vol.01-Vol.13]
[海王但丁][皆川亮二×泉福朗][Vol.01-Vol.13][境外版]
```

_命名建议修改自某喵_

## Issues & Pull Requests

欢迎提交新规则、问题、功能……

## 致谢

本项目部分代码及思路来自[Pfuenzle/AnisearchKomga](https://github.com/Pfuenzle/AnisearchKomga)，部分代码生成自[chatgpt](https://chat.openai.com/)，在此表示感谢！

语料库数据来源，感谢公开：

- `bangumi_person.txt`文件提取自[bangumi/Archive](https://github.com/bangumi/Archive)
- `Japanese_Names_Corpus（18W）.txt`文件来自[wainshine/Chinese-Names-Corpus](https://github.com/wainshine/Chinese-Names-Corpus)

另外，也感谢以下优秀项目：

- [gotson/komga](https://github.com/gotson/komga)
- [bangumi/api](https://github.com/bangumi/api)
