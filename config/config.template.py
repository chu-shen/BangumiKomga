# Connect Komga
# Get access token from: https://next.bgm.tv/demo/access-token
BANGUMI_ACCESS_TOKEN = 'gruUsn***************************SUSSn'
KOMGA_BASE_URL = "http://IP:PORT"
KOMGA_EMAIL = "email"
KOMGA_EMAIL_PASSWORD = "password"
KOMGA_LIBRARY_LIST = []
KOMGA_COLLECTION_LIST = []

# Poster Refresh
USE_BANGUMI_THUMBNAIL = False
USE_BANGUMI_THUMBNAIL_FOR_BOOK = False

# bangumi/Archive
# https://github.com/bangumi/Archive
USE_BANGUMI_ARCHIVE = False
ARCHIVE_FILES_DIR = "./archivedata/"

# Misc
# Title Sort Switch
SORT_TITLE = False
# Search Result Filter
FUZZ_SCORE_THRESHOLD = 80
# Recheck Behaviour
RECHECK_FAILED_SERIES = False
RECHECK_FAILED_BOOKS = False
CREATE_FAILED_COLLECTION = False

# External Notify Settings
# Support 'GOTIFY', 'WEBHOOK', 'HEALTHCHECKS'
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
