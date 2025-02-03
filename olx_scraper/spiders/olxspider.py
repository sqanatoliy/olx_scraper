import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterator, AsyncGenerator, Any

import scrapy
from decouple import config
from playwright.async_api import Browser, BrowserContext, Playwright, async_playwright
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from scrapy import signals
from scrapy.http import Response
from scrapy.selector.unified import SelectorList

from .playwright_helpers import (
    check_403_error,
    scroll_to_number_of_views,
    scroll_and_click_to_show_phone,
    wait_for_number_of_views, login_olx,
)
from ..items import OlxScraperItem

# OLX credentials
OLX_URL = "https://www.olx.ua/"
OLX_EMAIL = config("OLX_EMAIL")
OLX_PASSWORD = config("OLX_PASSWORD")

# path to the root of the project
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
STATE_FILE = PROJECT_ROOT / "state.json"
# Check that state.json exist else None
storage_state_path = str(STATE_FILE) if STATE_FILE.exists() else None

# ADS LIST PAGE
ADS_BLOCK_SELECTOR = 'div[data-testid="l-card"]'
AD_TITLE_URL_SELECTOR = ' div[data-cy="ad-card-title"] a'
AD_TITLE_SELECTOR = ' div[data-cy="ad-card-title"] a > h4'
AD_PRICE_SELECTOR = ' p[data-testid="ad-price"]'
AD_LOCATION_AND_DATE_SELECTOR = ' p[data-testid="location-date"]'

# AD DETAIL PAGE

# Contact section

AD_PUB_DATE_SELECTOR = 'span[data-cy="ad-posted-at"]'
BTN_SHOW_PHONE_SELECTOR = 'button[data-testid="show-phone"]'
CONTACT_PHONE_SELECTOR = 'a[data-testid="contact-phone"]'
# User profile
USER_NAME_SELECTOR = 'a[data-testid="user-profile-link"] h4'
USER_SCORE_SELECTOR = 'div[data-testid="score-widget"] > p'
USER_REGISTRATION_SELECTOR = 'a[data-testid="user-profile-link"] > div > div > p > span'
USER_LAST_SEEN_SELECTOR = 'p[data-testid="lastSeenBox"] > span'
# Location
MAP_OVERLAY_SELECTOR = 'div[data-testid="qa-map-overlay-hidden"]'
# Photo section
BLOCK_WITH_PHOTO_SELECTOR = 'div[data-testid="ad-photo"]'
# Description section
AD_TAGS_SELECTOR = (
    'div[data-testid="ad-promotion-actions"] + div[data-testid="qa-advert-slot"] + div > div'
)
DESCRIPTION_PARTS_SELECTOR = 'div[data-cy="ad_description"] > div'
# Description section footer
FOOTER_BAR_SELECTOR = 'div[data-testid="ad-footer-bar-section"]'
AD_ID_SELECTOR = 'div[data-testid="ad-footer-bar-section"] > span'
AD_VIEW_COUNTER_SELECTOR = 'span[data-testid="page-view-counter"]'


class OlxSpider(scrapy.Spider):
    """Scraper for olx.ua/list"""

    name = "olx"
    allowed_domains: list[str] = ["olx.ua"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.browser = None
        self.context = None
        self.playwright = None

    async def open_spider(self, spider):
        """Start Playwright """
        self.logger.info("Starting Playwright...")
        # get PLAYWRIGHT_LAUNCH_OPTIONS from settings.py
        launch_options = spider.settings.getdict("PLAYWRIGHT_LAUNCH_OPTIONS")
        self.playwright: Playwright = await async_playwright().start()
        self.browser: Browser = await self.playwright.chromium.launch(**launch_options, )
        self.context: BrowserContext = await self.browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            java_script_enabled=True,
            timezone_id="Europe/Kiev",
            locale="uk-UA",
            extra_http_headers={
                "Accept-Language": "uk-UA,uk;q=0.9",
                "Referer": f"{OLX_URL}",
            },
            storage_state=storage_state_path
        )
        await login_olx(self.context, OLX_URL, OLX_EMAIL, OLX_PASSWORD, self)
        if self.context:
            self.logger.info("Playwright started successfully!")
        else:
            self.logger.error("Error Playwright! self.context or self.browser = None")

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        """Scrapy passes a `crawler` to give access to the `settings`"""
        spider = super().from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(spider.open_spider, signal=signals.spider_opened)
        crawler.signals.connect(spider.close_spider, signal=signals.spider_closed)

        # # Start async Playwright
        # asyncio.ensure_future(spider.init_playwright())

        # Get value from settings.py
        spider.start_page = crawler.settings.getint("START_PAGE", 1)
        spider.end_page = crawler.settings.getint("END_PAGE", 6)
        spider.start_urls = [
            f"{OLX_URL}uk/list/?page={i}" for i in range(spider.start_page, spider.end_page + 1)
        ]
        return spider

    # async def init_playwright(self):
    #     """Start Playwright before scraping"""
    #     self.logger.info("Starting Playwright...")
    #     self.playwright = await async_playwright().start()
    #     self.browser = await self.playwright.chromium.launch(headless=True)
    #     self.context = await self.browser.new_context(viewport={"width": 1980, "height": 1020})
    #     if self.context:
    #         self.logger.info("Playwright started successfully!")
    #     else:
    #         self.logger.error("Error Playwright! self.context or self.browser = None")

    def start_requests(self) -> Iterator[scrapy.Request]:
        """Override start_requests to include Playwright meta"""
        for url in self.start_urls:
            self.logger.debug(f"Generating request for URL: {url}")
            yield scrapy.Request(
                url=url,
                callback=self.parse,
                meta={
                    "context": self.context
                },
                errback=self.errback_close_page,
            )

    def parse(self, response: Response) -> Iterator[scrapy.Request]:
        """Get all urls"""
        context = response.meta["context"]
        self.logger.info(f"Parsing response from {response.url}")
        ads_block: SelectorList = response.css(ADS_BLOCK_SELECTOR)
        if not ads_block:
            self.logger.warning(f"No ads found on the page: {response.url}")
            return
        for ad in ads_block[:]:
            self.logger.debug(f"Ad block found: {ad.get()[:100]}")
            ad_link: str | None = (
                ad.css(AD_TITLE_URL_SELECTOR).css("::attr(href)").get()
            )
            if not ad_link:
                continue
            ad_title: str | None = ad.css(AD_TITLE_SELECTOR).css("::text").get()
            ad_price: str | None = ad.css(AD_PRICE_SELECTOR).css("::text").get()
            full_url: str = response.urljoin(ad_link)
            if "/d/uk/" not in full_url:
                full_url = full_url.replace("/d/", "/d/uk/")
            self.logger.info(f"Collected URL: {full_url}")
            # Create Item and fill fields
            item: OlxScraperItem = OlxScraperItem()
            item["title"] = ad_title.strip()
            item["price"] = ad_price.strip() if ad_price else None
            item["url"] = full_url.strip()
            yield scrapy.Request(
                url=full_url,
                callback=self.parse_ad,
                meta={
                    "item": item, "context": context
                },
                errback=self.errback_close_page,
            )

    async def parse_ad(
            self, response: Response
    ) -> AsyncGenerator[OlxScraperItem, None]:
        """Processing the detailed page of the ad"""
        context = response.meta["context"]
        if not context:
            self.logger.error("❌ Playwright context not passed in parse_ad()!")
            return

        page = await context.new_page()
        try:
            start_time = time.time()
            await page.goto(response.url, wait_until="domcontentloaded")
            self.logger.info(f"✅ Loaded {response.url} in {time.time() - start_time:.2f}s")
            item: OlxScraperItem = response.meta["item"]

            await check_403_error(page, response.url, self)
            await scroll_to_number_of_views(page, FOOTER_BAR_SELECTOR, USER_NAME_SELECTOR, DESCRIPTION_PARTS_SELECTOR, self)
            await wait_for_number_of_views(page, AD_VIEW_COUNTER_SELECTOR, self)

            # -- ⬇️ Using variables to improve readability ⬇️ --
            ad_pub_date_locator = page.locator(AD_PUB_DATE_SELECTOR)
            user_name_locator = page.locator(USER_NAME_SELECTOR).first
            user_score_locator = page.locator(USER_SCORE_SELECTOR).first
            user_registration_locator = page.locator(USER_REGISTRATION_SELECTOR).first
            user_last_seen_locator = page.locator(USER_LAST_SEEN_SELECTOR).first
            ad_id_locator = page.locator(AD_ID_SELECTOR).first
            ad_view_counter_locator = page.locator(AD_VIEW_COUNTER_SELECTOR)
            contact_phone_locator = page.locator(CONTACT_PHONE_SELECTOR)

            # Ad publication date
            ad_pub_date = await ad_pub_date_locator.text_content()

            # User profile
            user_name = await user_name_locator.first.text_content()
            user_score = (
                await user_score_locator.first.text_content()
                if await user_score_locator.first.is_visible(timeout=1000)
                else "Ще не має рейтингу"
            )
            user_registration = await user_registration_locator.text_content()
            user_last_seen = (
                await user_last_seen_locator.first.text_content()
                if await user_last_seen_locator.first.is_visible(timeout=100)
                else None
            )

            # Location
            map_overlay = page.locator(MAP_OVERLAY_SELECTOR)
            location_section = map_overlay.locator("..")
            location_parts = await location_section.locator("svg + div *").all_text_contents()
            location = " ".join(loc.strip() for loc in location_parts if loc)

            # Extracting images
            block_with_locator = page.locator(BLOCK_WITH_PHOTO_SELECTOR)
            if await block_with_locator.first.is_visible(timeout=1_000):
                img_elements = await block_with_locator.locator("img").all()
                img_urls_list = [await img.get_attribute("src") for img in img_elements if await img.get_attribute("src")]
            else:
                img_urls_list = ["Ad does not have photos"]

            # Extracting tags and description
            ad_tags_locator = page.locator(AD_TAGS_SELECTOR)
            ad_tags = (
                await ad_tags_locator.all_text_contents()
                if await ad_tags_locator.first.is_visible(timeout=1000)
                else ["Ad doesnt have tags"]
            )

            description_parts = await page.locator(DESCRIPTION_PARTS_SELECTOR).all_text_contents()
            description = " ".join(part.strip() for part in description_parts if part)

            # Extracting ad ID and view counter
            ad_id = await ad_id_locator.text_content()

            ad_view_counter = (
                await ad_view_counter_locator.text_content()
                if await ad_view_counter_locator.is_visible(timeout=3_000)
                else "Ad doesnt have view"
            )
            item["ad_pub_date"] = self.parse_date(ad_pub_date)
            item["user_name"] = user_name.strip() if user_name else None
            item["user_score"] = user_score if user_score else None
            item["user_registration"] = (
                user_registration.strip() if user_registration else None
            )
            item["user_last_seen"] = (
                self.parse_date(user_last_seen)
                if user_last_seen
                else self.parse_date("Сьогодні")
            )
            item["ad_id"] = ad_id
            item["ad_view_counter"] = ad_view_counter if ad_view_counter else None
            item["location"] = location.strip() if location else None
            item["ad_tags"] = ad_tags
            item["description"] = description if description else None
            item["img_src_list"] = img_urls_list

            await scroll_and_click_to_show_phone(
                page,
                BTN_SHOW_PHONE_SELECTOR,
                CONTACT_PHONE_SELECTOR,
                self,
            )

            phone_number = (
                await contact_phone_locator.first.text_content()
                if await contact_phone_locator.first.is_visible(timeout=2000)
                else "N/A"
            )

            item["phone_number"] = phone_number
            self.logger.info(f"📞 Phone number extracted: {phone_number}")
            # Save data
            yield item
        except PlaywrightTimeoutError as err:
            self.logger.error(f"⏳ Timeout error while parsing {response.url}: {err}")
        except Exception as e:
            self.logger.error(f"❌ Unexpected error in parse_ad: {e}", exc_info=True)
        finally:
            await page.close()

    async def close_spider(self, spider):
        """Закриваємо Playwright після завершення роботи"""
        self.logger.info("Закриваємо Playwright...")
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()

    async def errback_close_page(self, failure) -> None:
        meta: Any = failure.request.meta
        if "playwright_page" in meta:
            page: Any = meta.get("page")
            if not page:
                self.logger.warning(f"No Playwright page found in meta for request {failure.request.url}. Unable to close.")
                return
            try:
                self.logger.error(f"Error encountered: {failure}. Closing page for request {failure.request.url}")
                await page.close()
                self.logger.info(f"Page for {failure.request.url} closed successfully after exception.")
            except Exception as e:
                self.logger.error(f"Failed to close page for {failure.request.url}: {e}")

    def parse_date(self, input_str) -> str:
        """Parse a string with a date and returns it in the '15 січня 2025 р.' format."""
        today: datetime = datetime.now()
        months_uk: dict[int, str] = {
            1: "січня",
            2: "лютого",
            3: "березня",
            4: "квітня",
            5: "травня",
            6: "червня",
            7: "липня",
            8: "серпня",
            9: "вересня",
            10: "жовтня",
            11: "листопада",
            12: "грудня",
        }
        if input_str.startswith("Сьогодні"):
            full_date: str = today.strftime(f"%d {months_uk[today.month]} %Y р.")
        elif input_str.startswith("Онлайн вчора"):
            yesterday = today - timedelta(days=1)
            full_date: str = yesterday.strftime(
                f"%d {months_uk[yesterday.month]} %Y р."
            )
        elif input_str.startswith("Онлайн в "):
            full_date: str = today.strftime(f"%d {months_uk[today.month]} %Y р.")
        elif input_str.startswith("Онлайн "):
            input_str = input_str[len("Онлайн "):]
            match: re.Match[str] | None = re.match(
                r"(\d{1,2}) ([а-яіїє]+) (\d{4}) р.", input_str
            )
            if not match:
                self.logger.warning("Некоректний формат дати: %s", input_str)
                return ""
            day: str = match.group(1).zfill(2)
            month: str = match.group(2)
            year: str = match.group(3)
            if month not in months_uk.values():
                self.logger.warning("Некоректний місяць у даті: %s", month)
            full_date = f"{day} {month} {year} р."
        else:
            match: re.Match[str] | None = re.match(
                r"(\d{1,2}) ([а-яіїє]+) (\d{4}) р.", input_str
            )
            if not match:
                self.logger.warning("Некоректний формат дати: %s", input_str)
            day: str | Any = match.group(1).zfill(2)
            month: str | Any = match.group(2)
            year: str = match.group(3)
            if month not in months_uk.values():
                self.logger.warning("Некоректний місяць у даті: %s", month)
            full_date = f"{day} {month} {year} р."
        return full_date
