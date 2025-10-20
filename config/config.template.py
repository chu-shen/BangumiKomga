# @@name: BANGUMI_ACCESS_TOKEN
# @@prompt: BGM访问令牌
# @@type: password
# @@required: false
# @@validator: validate_bangumi_token
# @@info: 获取地址: https://next.bgm.tv/demo/access-token
# @@version: 0.1
BANGUMI_ACCESS_TOKEN = ''


# @@name: KOMGA_BASE_URL
# @@prompt: KOMGA访问地址
# @@type: url
# @@required: True
# @@validator: validate_url
# @@info: http://IP:PORT
# @@version: 0.1
KOMGA_BASE_URL = ""

# @@name: KOMGA_EMAIL
# @@prompt: KOMGA账户邮箱地址
# @@type: string
# @@required: True
# @@validator: validate_email
# @@version: 0.1
KOMGA_EMAIL = ""

# @@name: KOMGA_EMAIL_PASSWORD
# @@prompt: KOMGA账户密码
# @@type: password
# @@required: True
# @@validator: validate_komga_access
# @@version: 0.1
KOMGA_EMAIL_PASSWORD = ""


# @@name: KOMGA_LIBRARY_LIST
# @@prompt: 配置 KOMGA 库
# @@type: list
# @@required: False
# @@validator:
# @@info: 将使用 KOMGA 配置读取库列表。配置示例：[{"LIBRARY": "0BYYYYABE9EAV", "IS_NOVEL_ONLY": False}]
# @@version: 0.18.0
KOMGA_LIBRARY_LIST = []
# @@name: KOMGA_COLLECTION_LIST
# @@prompt: 配置 KOMGA 收藏
# @@type: list
# @@required: False
# @@validator:
# @@info: 将使用 KOMGA 配置读取收藏列表。配置示例：[{"COLLECTION": "0BCWTYYCYYY4C", "IS_NOVEL_ONLY": True}]
# @@version: 0.18.0
KOMGA_COLLECTION_LIST = []


# @@name: USE_BANGUMI_ARCHIVE
# @@prompt: 是否启用本地离线元数据
# @@type: boolean
# @@required: False
# @@validator:
# @@info: 指定是否启用本地 bangumi/Archive 离线元数据
# @@version: 0.13.0
USE_BANGUMI_ARCHIVE = False

# @@name: ARCHIVE_FILES_DIR
# @@prompt: 本地离线元数据存储目录
# @@type: string
# @@required: False
# @@validator:
# @@info: 可以指定自建目录
# @@version: 0.13.0
ARCHIVE_FILES_DIR = "./archivedata/"

# @@name: ARCHIVE_UPDATE_INTERVAL
# @@prompt: 离线元数据的更新间隔
# @@type: integer
# @@required: False
# @@validator:
# @@info: 单位为小时的整数值, 置为 0 表示不检查离线元数据更新
# @@version: 0.13.0
ARCHIVE_UPDATE_INTERVAL = 168

# @@name: BANGUMI_KOMGA_SERVICE_TYPE
# @@prompt: BangumiKomga 服务运行方式
# @@type: string
# @@required: False
# @@validator:
# @@info: 可选值：'once', 'poll', 'sse'
# @@allowed_values: once, poll, sse
# @@version: 0.15.0
BANGUMI_KOMGA_SERVICE_TYPE = "once"

# @@name: BANGUMI_KOMGA_SERVICE_POLL_INTERVAL
# @@prompt: 轮询服务轮询间隔
# @@type: integer
# @@required: False
# @@validator:
# @@info: 单位为秒的整数值
# @@version: 0.15.0
BANGUMI_KOMGA_SERVICE_POLL_INTERVAL = 20

# @@name: BANGUMI_KOMGA_SERVICE_POLL_REFRESH_ALL_METADATA_INTERVAL
# @@prompt: 轮询服务全量刷新间隔
# @@type: integer
# @@required: False
# @@validator:
# @@info: 整数值, 指定多少次轮询后执行一次全量刷新
# @@version: 0.15.0
BANGUMI_KOMGA_SERVICE_POLL_REFRESH_ALL_METADATA_INTERVAL = 10000

# @@name: USE_BANGUMI_THUMBNAIL
# @@prompt: 是否使用 Bangumi 封面替换系列海报
# @@type: boolean
# @@required: False
# @@validator:
# @@info: 设置为`True`且未曾上传过系列海报时，使用 Bangumi 封面替换系列海报
# @@version: 0.5.0
USE_BANGUMI_THUMBNAIL = False

# @@name: USE_BANGUMI_THUMBNAIL_FOR_BOOK
# @@prompt: 是否使用 Bangumi 封面替换单册海报
# @@type: boolean
# @@required: False
# @@validator:
# @@info: 设置为`True`且未曾上传过单册海报时，使用 Bangumi 封面替换单册海报
# @@version: 0.6.0
USE_BANGUMI_THUMBNAIL_FOR_BOOK = False

# @@name: SORT_TITLE
# @@prompt: 添加一个首字母用于导航
# @@type: boolean
# @@required: False
# @@validator:
# @@info: 设置为`True`时，在刷新元数据后会在系列元数据-排序标题前添加一个首字母用于导航。此为临时方案
# @@version: 0.10.0
SORT_TITLE = False

# @@name: FUZZ_SCORE_THRESHOLD
# @@prompt: 过滤搜索结果的相似度阈值
# @@type: integer
# @@required: False
# @@validator:
# @@info: 整数值, 满分 100，默认值`80`。用于过滤搜索结果
# @@version: 0.12.0
FUZZ_SCORE_THRESHOLD = 80
# 重新刷新
# @@name: RECHECK_FAILED_SERIES
# @@prompt: 重新检查刷新元数据失败的系列
# @@type: boolean
# @@required: False
# @@validator:
# @@info: 重新检查刷新元数据失败的系列
# @@version: 0.1
RECHECK_FAILED_SERIES = False
# @@name: RECHECK_FAILED_BOOKS
# @@prompt: 重新检查刷新元数据失败的书
# @@type: boolean
# @@required: False
# @@validator:
# @@info: 重新检查刷新元数据失败的书
# @@version: 0.1
RECHECK_FAILED_BOOKS = False

# @@name: CREATE_FAILED_COLLECTION
# @@prompt: 创建失败收藏
# @@type: boolean
# @@required: False
# @@validator:
# @@info: 置为`True`时，程序会在刷新完成后，将**本次**刷新失败的系列添加到指定收藏（默认名：`FAILED_COLLECTION`）。
# @@version: 0.1
CREATE_FAILED_COLLECTION = False


# @@name: NOTIF_TYPE_ENABLE
# @@prompt: 设置消息通知类型
# @@type: list
# @@required: False
# @@default: []
# @@info: 可选值：'GOTIFY', 'WEBHOOK', 'HEALTHCHECKS'
# @@allowed_values: GOTIFY, WEBHOOK, HEALTHCHECKS
# @@version: 0.1
NOTIF_TYPE_ENABLE = []

# @@name: NOTIF_GOTIFY_ENDPOINT
# @@prompt: GOTIFY 地址
# @@type: url
# @@required: False
# @@validator: validate_url
# @@info:
# @@version: 0.1
NOTIF_GOTIFY_ENDPOINT = "http://IP:PORT"
# @@name: NOTIF_GOTIFY_TOKEN
# @@prompt: GOTIFY TOKEN
# @@type: string
# @@required: False
# @@validator:
# @@info:
# @@version: 0.1
NOTIF_GOTIFY_TOKEN = "TOKEN"
# @@name: NOTIF_GOTIFY_PRIORITY
# @@prompt: GOTIFY 优先级
# @@type: integer
# @@required: False
# @@validator:
# @@info:
# @@version: 0.1
NOTIF_GOTIFY_PRIORITY = 1
# @@name: NOTIF_GOTIFY_TIMEOUT
# @@prompt: GOTIFY 请求超时
# @@type: integer
# @@required: False
# @@validator:
# @@info:
# @@version: 0.1
NOTIF_GOTIFY_TIMEOUT = 10

# @@name: NOTIF_WEBHOOK_ENDPOINT
# @@prompt: WEBHOOK 地址
# @@type: url
# @@required: False
# @@validator: validate_url
# @@info: 比如飞书、钉钉等
# @@version: 0.1
NOTIF_WEBHOOK_ENDPOINT = "http://IP:PORT"
# @@name: NOTIF_WEBHOOK_METHOD
# @@prompt: WEBHOOK 方法
# @@type: string
# @@required: False
# @@validator:
# @@info:
# @@version: 0.1
NOTIF_WEBHOOK_METHOD = "POST"
# @@name: NOTIF_WEBHOOK_HEADER
# @@prompt: WEBHOOK 请求头
# @@type: string
# @@required: False
# @@validator:
# @@info:
# @@version: 0.1
NOTIF_WEBHOOK_HEADER = '{"Content-Type": "application/json"}'
# @@name: NOTIF_WEBHOOK_TIMEOUT
# @@prompt: WEBHOOK 请求超时
# @@type: integer
# @@required: False
# @@validator:
# @@info:
# @@version: 0.1
NOTIF_WEBHOOK_TIMEOUT = 10

# @@name: NOTIF_HEALTHCHECKS_ENDPOINT
# @@prompt: HEALTHCHECKS 地址
# @@type: url
# @@required: False
# @@validator: validate_url
# @@info:
# @@version: 0.1
NOTIF_HEALTHCHECKS_ENDPOINT = "http://IP:PORT"
# @@name: NOTIF_HEALTHCHECKS_TIMEOUT
# @@prompt: HEALTHCHECKS 请求超时
# @@type: integer
# @@required: False
# @@validator:
# @@info:
# @@version: 0.1
NOTIF_HEALTHCHECKS_TIMEOUT = 10
