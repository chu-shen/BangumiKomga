import requests
from config.config import *
from tools.log import logger


def send_notification(title, message):
    for type in NOTIF_TYPE_ENABLE:
        if type == "GOTIFY":
            data = {
                "title": "BangumiKomga: " + title,
                "message": message,
                "priority": NOTIF_GOTIFY_PRIORITY,
                "extras": {
                    "client::display": {
                        # It is recommended to use text/plain to reduce possible security issues
                        # when using text from external sources like f.ex. output from scripts.
                        "contentType": "text/markdown"
                    },
                    "client::notification": {"click": {"url": KOMGA_BASE_URL}},
                },
            }
            response = requests.post(
                NOTIF_GOTIFY_ENDPOINT + "/message?token=" + NOTIF_GOTIFY_TOKEN,
                timeout=NOTIF_GOTIFY_TIMEOUT,
                json=data,
            )
            if response.status_code == 200:
                logger.info(type + ": Notification sent successfully.")
            else:
                logger.error(type + ": Failed to send notification.")

        elif type == "WEBHOOK":
            data = {
                "msg_type": "interactive",
                "card": {
                    "header": {
                        "template": "blue",
                        "title": {
                            "content": "BangumiKomga: " + title,
                            "tag": "plain_text",
                        },
                    },
                    "elements": [
                        {"tag": "div", "text": {"content": message, "tag": "lark_md"}}
                    ],
                },
            }
            response = requests.request(
                NOTIF_WEBHOOK_METHOD,
                NOTIF_WEBHOOK_ENDPOINT,
                headers=NOTIF_WEBHOOK_HEADER,
                timeout=NOTIF_WEBHOOK_TIMEOUT,
                json=data,
            )
            if response.status_code == 200:
                logger.info(type + ": Notification sent successfully.")
            else:
                logger.error(type + ": Failed to send notification.")

        elif type == "HEALTHCHECKS":
            try:
                requests.get(
                    NOTIF_HEALTHCHECKS_ENDPOINT, timeout=NOTIF_HEALTHCHECKS_TIMEOUT
                )
            except requests.RequestException as e:
                # Log ping failure here...
                logger.error(type + ": Ping failed: " + e)
