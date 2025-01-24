import logging
import logging.config
from config.config import LOGGING_CONFIG

# Настройка логирования
logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger('twitter_parser') 