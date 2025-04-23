import sys
import logging
from logging.handlers import RotatingFileHandler

logger = logging.getLogger()
logger.setLevel(logging.INFO)
formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(filename)-8s : %(lineno)s - %(message)s")

fh = RotatingFileHandler(filename='logs/refreshMetadata.log', maxBytes=10000000, backupCount=9, encoding='utf-8')
fh.setFormatter(formatter)
logger.addHandler(fh)

sh=logging.StreamHandler(sys.stdout)
sh.setFormatter(formatter)
logger.addHandler(sh)