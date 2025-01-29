import logging
from scrapy.utils.log import configure_logging
from logging.handlers import RotatingFileHandler
import os
from decouple import config


# Disable default Scrapy log settings.
configure_logging(install_root_handler=False)

START_PAGE = 1
END_PAGE = 5

# === Basic Scrapy setting ===
BOT_NAME = "olx_scraper"  # Project name Scrapy
SPIDER_MODULES = ["olx_scraper.spiders"]  # way to the modules with spiders
NEWSPIDER_MODULE = "olx_scraper.spiders"  # way to create new spiders

LOG_LEVEL = "DEBUG"  # Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
CONCURRENT_REQUESTS = 1  # Number of concurrent requests
DOWNLOAD_DELAY = 1  # Delay between requests (in seconds)

PLAYWRIGHT_BROWSER_TYPE = "chromium"  # Type of browser used Playwright
PLAYWRIGHT_LAUNCH_OPTIONS = {
    "headless": True,  # Run in headless mode
    "args": ["--no-sandbox", "--disable-setuid-sandbox"],
}

USER_AGENT = None  # Scrapy User Agent
DEFAULT_REQUEST_HEADERS = {
    "User-Agent": USER_AGENT,  
    "Accept-Language": "en-US,en;q=0.9,uk-UA;q=0.8,uk;q=0.7",  
    "Referer": "https://www.olx.ua/",  
    "Connection": "keep-alive",  
}

DOWNLOAD_HANDLERS = {
    "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",  # Using Playwright for HTTP requests
    "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",  # Using Playwright for HTTPS requests
}

PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT = 30_000

ITEM_PIPELINES = {
    "olx_scraper.pipelines.PostgresPipeline": 300,  # Using PostgresPipeline to process data
}

# === Database settings ===
POSTGRES_URI = config("POSTGRES_URI", default="localhost")
POSTGRES_DB = config("POSTGRES_DB", default="olx_db")
POSTGRES_USER = config("POSTGRES_USER", default="user")
POSTGRES_PASSWORD = config("POSTGRES_PASSWORD", default="password")

ROBOTSTXT_OBEY = False  # Ignoring robots.txt rules

# === Logging directory settings ===
LOG_DIR = "logs"  # Directory for saving logs
LOG_FILE = os.path.join(LOG_DIR, "olx_scraper.log")  # Full path to the log file
MAX_LOG_FILE_SIZE = 1 * 1024 * 1024 * 1024  # Maximum size of the log file (1 GB)
BACKUP_COUNT = 5  # Number of backup copies of logs


# Create a directory for logs
os.makedirs(LOG_DIR, exist_ok=True)

# Logging settings
logger = logging.getLogger()  # Initializing logger
logger.setLevel(LOG_LEVEL)  # Setting the logging level

# Rotation of logs
rotating_handler = RotatingFileHandler(
    LOG_FILE, maxBytes=MAX_LOG_FILE_SIZE, backupCount=BACKUP_COUNT
)  # Creating a handler to rotate log files
formatter = logging.Formatter(
    "%(asctime)s [%(levelname)s] %(name)s [%(funcName)s]: %(message)s"
)
rotating_handler.setFormatter(formatter)
# rotating_handler.setLevel(logging.DEBUG)  # Setting the logging level (if different from general)
logger.addHandler(rotating_handler)  # Adding a handler to the logger

# Stream Handler for console output
console_handler = logging.StreamHandler()
console_formatter = logging.Formatter("%(asctime)s [%(levelname)s]: %(message)s")
console_handler.setFormatter(console_formatter)
console_handler.setLevel(logging.INFO)  # Show only INFO level and above in terminal
logger.addHandler(console_handler)


# === =================== ===
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"  # Compatible with new versions of Twisted
FEED_EXPORT_ENCODING = "utf-8"  # UTF-8 encoding for data export
