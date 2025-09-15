# type 可选值 : password, string, url, boolean, integer


# @@name: BANGUMI_ACCESS_TOKEN
# @@prompt: BGM访问令牌
# @@type: password
# @@required: True
# @@validator: validate_bangumi_token
# @@info: 获取地址: https://next.bgm.tv/demo/access-token
BANGUMI_ACCESS_TOKEN = 'gruUsn***************************SUSSn'


# @@name: KOMGA_BASE_URL
# @@prompt: KOMGA访问地址
# @@type: url
# @@required: True
# @@validator: validate_url
# @@info:
KOMGA_BASE_URL = "http://IP:PORT"

# @@name: KOMGA_EMAIL
# @@prompt: KOMGA账户邮箱地址
# @@type: string
# @@required: True
# @@validator: validate_email
KOMGA_EMAIL = "email"

# @@name: KOMGA_EMAIL_PASSWORD
# @@prompt: KOMGA账户密码
# @@type: password
# @@required: True
# @@validator: validate_komga_access
KOMGA_EMAIL_PASSWORD = "password"


# @@name: KOMGA_LIBRARY_LIST
# @@prompt: 开始 KOMGA 库交互式设置
# @@type: string
# @@required: False
# @@validator: validate_komga_libraries
# @@info: TODO: 未兼容此模式，此配置暂不可用。将使用 KOMGA_BASE_URL, KOMGA_EMAIL 和 KOMGA_EMAIL_PASSWORD 读取库列表
KOMGA_LIBRARY_LIST = []
KOMGA_COLLECTION_LIST = []
# 只应用于 Komga 的小说库
# TODO 适配不同库的 IS_NOVEL_ONLY 参数
IS_NOVEL_ONLY = False


# @@name: USE_BANGUMI_ARCHIVE
# @@prompt: 是否启用本地离线元数据
# @@type: boolean
# @@required: False
# @@validator:
# @@info: 指定是否启用本地 bangumi/Archive 离线元数据
USE_BANGUMI_ARCHIVE = False

# @@name: ARCHIVE_FILES_DIR
# @@prompt: 本地离线元数据存储目录
# @@type: string
# @@required: False
# @@validator:
# @@info: 可以指定自建目录
ARCHIVE_FILES_DIR = "./archivedata/"

# @@name: ARCHIVE_UPDATE_INTERVAL
# @@prompt: 离线元数据的更新间隔
# @@type: integer
# @@required: False
# @@validator:
# @@info: 单位为小时的整数值, 置为 0 表示不检查离线元数据更新
ARCHIVE_UPDATE_INTERVAL = 168

# @@name: BANGUMI_KOMGA_SERVICE_TYPE
# @@prompt: BangumiKomga 服务运行方式
# @@type: string
# @@required: False
# @@validator:
# @@info: 可选值：'once', 'poll', 'sse'
# @@allowed_values: once, poll, sse
BANGUMI_KOMGA_SERVICE_TYPE = "once"

# @@name: BANGUMI_KOMGA_SERVICE_POLL_INTERVAL
# @@prompt: 轮询服务轮询间隔
# @@type: integer
# @@required: False
# @@validator:
# @@info: 单位为秒的整数值
BANGUMI_KOMGA_SERVICE_POLL_INTERVAL = 20

# @@name: BANGUMI_KOMGA_SERVICE_POLL_REFRESH_ALL_METADATA_INTERVAL
# @@prompt: 轮询服务全量刷新间隔
# @@type: integer
# @@required: False
# @@validator:
# @@info: 整数值, 指定多少次轮询后执行一次全量刷新
BANGUMI_KOMGA_SERVICE_POLL_REFRESH_ALL_METADATA_INTERVAL = 10000

# Misc
# 海报
USE_BANGUMI_THUMBNAIL = False
USE_BANGUMI_THUMBNAIL_FOR_BOOK = False
# 字母导航
SORT_TITLE = False
# 搜索结果过滤
FUZZ_SCORE_THRESHOLD = 80
# 重新刷新
RECHECK_FAILED_SERIES = False
RECHECK_FAILED_BOOKS = False
# 创建收藏
CREATE_FAILED_COLLECTION = False


# @@name: NOTIF_TYPE_ENABLE
# @@prompt: 设置消息通知类型
# @@type: string
# @@required: False
# @@default: []
# @@info: 消息通知
# @@info: 可选值：'GOTIFY', 'WEBHOOK', 'HEALTHCHECKS'
# @@allowed_values: GOTIFY, WEBHOOK, HEALTHCHECKS
NOTIF_TYPE_ENABLE = []

NOTIF_GOTIFY_ENDPOINT = "http://IP:PORT"
NOTIF_GOTIFY_TOKEN = "TOKEN"
NOTIF_GOTIFY_PRIORITY = 1
NOTIF_GOTIFY_TIMEOUT = 10

NOTIF_WEBHOOK_ENDPOINT = "http://IP:PORT"
NOTIF_WEBHOOK_METHOD = "POST"
NOTIF_WEBHOOK_HEADER = {"Content-Type": "application/json"}
NOTIF_WEBHOOK_TIMEOUT = 10

NOTIF_HEALTHCHECKS_ENDPOINT = "http://IP:PORT"
NOTIF_HEALTHCHECKS_TIMEOUT = 10
