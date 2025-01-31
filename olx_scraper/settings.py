import logging
import os
from scrapy.utils.log import configure_logging
from logging.handlers import RotatingFileHandler
from decouple import config

from olx_scraper.pipelines import PostgresPipeline

# Range of pages of the list of ads (olx.ua/list)
START_PAGE = 1
END_PAGE = 5

# === Basic Scrapy setting ===
BOT_NAME = "olx_scraper"  # Project name Scrapy
SPIDER_MODULES = ["olx_scraper.spiders"]  # way to the modules with spiders
NEWSPIDER_MODULE = "olx_scraper.spiders"  # way to create new spiders

# === Scrapy Performance Settings ===
CONCURRENT_REQUESTS = 1
DOWNLOAD_DELAY = 1

# === Playwright Settings ===
PLAYWRIGHT_BROWSER_TYPE = "chromium"
PLAYWRIGHT_LAUNCH_OPTIONS = {
    "headless": True,
    "args": ["--no-sandbox", "--disable-setuid-sandbox"],
}
PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT = 30_000

# === HTTP Headers ===
USER_AGENT = None
DEFAULT_REQUEST_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept-Language": "en-US,en;q=0.9,uk-UA;q=0.8,uk;q=0.7",
    "Referer": "https://www.olx.ua/",
    "Connection": "keep-alive",
}

# === Download Handlers ===
DOWNLOAD_HANDLERS = {
    "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
    "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
}

# === Pipelines ===
ITEM_PIPELINES = {
    "olx_scraper.pipelines.PostgresPipeline": 300,  # Using PostgresPipeline to process data
}


# === Database settings ===

# === Database Settings ===
POSTGRES_URI = config("POSTGRES_URI", default="localhost")
POSTGRES_DB = config("POSTGRES_DB", default="olx_db")
POSTGRES_USER = config("POSTGRES_USER", default="user")
POSTGRES_PASSWORD = config("POSTGRES_PASSWORD", default="password")

# === Other Settings ===
ROBOTSTXT_OBEY = False  # Ignoring robots.txt rules
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"  # Compatible with new versions of Twisted
FEED_EXPORT_ENCODING = "utf-8"  # UTF-8 encoding for data export

# === Logging Settings ===
LOG_LEVEL = "INFO"
# === Logging directory settings ===
LOGS_DIR = "logs"  # Directory for saving logs
LOGS_FILE = os.path.join(LOGS_DIR, "olx_scraper.log")  # Full path to the log file
MAX_LOG_FILE_SIZE = 1 * 1024 * 1024 * 1024  # Maximum size of the log file (1 GB)
BACKUP_COUNT = 5  # Number of backup copies of logs

# Ensure logs directory exists
os.makedirs(LOGS_DIR, exist_ok=True)

# Configure Scrapy Logging
configure_logging(install_root_handler=False)
logger = logging.getLogger()

# Remove existing FileHandlers to avoid duplicates
logger.handlers = [
    handler for handler in logger.handlers if not isinstance(handler, logging.FileHandler)
]

logger.setLevel(LOG_LEVEL)

# Rotating File Handler (Logs to file with rotation)
rotating_handler = RotatingFileHandler(
    LOGS_FILE, maxBytes=MAX_LOG_FILE_SIZE, backupCount=BACKUP_COUNT
)  # Creating a handler to rotate log files
formatter = logging.Formatter(
    "%(asctime)s [%(levelname)s] %(name)s [%(funcName)s]: %(message)s"
)
rotating_handler.setFormatter(formatter)
rotating_handler.setLevel(logging.INFO)  # Setting the logging level (if different from general)
logger.addHandler(rotating_handler)  # Adding a handler to the logger

# Console Handler (Logs to terminal)
if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s]: %(message)s"))
    console_handler.setLevel(logging.INFO)
    logger.addHandler(console_handler)
