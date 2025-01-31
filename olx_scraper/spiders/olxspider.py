import re
from datetime import datetime, timedelta
from typing import Iterator, AsyncGenerator, Any

import scrapy
from playwright.async_api import async_playwright
from scrapy import signals
from scrapy.http import Response
from scrapy.selector.unified import SelectorList

from .playwright_helpers import (
    check_403_error,
    scroll_to_number_of_views,
    scroll_and_click_to_show_phone,
    wait_for_number_of_views,
)
from ..items import OlxScraperItem

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
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True)
        self.context = await self.browser.new_context(viewport={"width": 1980, "height": 1020})
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
            f"https://www.olx.ua/uk/list/?page={i}" for i in range(spider.start_page, spider.end_page + 1)
        ]

        spider.db_pipeline = crawler.settings.get('POSTGRES_PIPELINE')
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
        page = await context.new_page()
        if not context:
            self.logger.error("Playwright context not passed in parse_ad()!")
            return
        try:
            await page.goto(response.url, wait_until="domcontentloaded")
            item: OlxScraperItem = response.meta["item"]

            await check_403_error(page, response.url, self)
            await scroll_to_number_of_views(page, FOOTER_BAR_SELECTOR, USER_NAME_SELECTOR, DESCRIPTION_PARTS_SELECTOR, self)
            await wait_for_number_of_views(page, AD_VIEW_COUNTER_SELECTOR, self)

            # Ad publication date
            ad_pub_date: str | None = await page.locator(AD_PUB_DATE_SELECTOR).text_content()

            # User profile
            user_name: str | None = await page.locator(USER_NAME_SELECTOR).first.text_content()
            user_score_element = page.locator(USER_SCORE_SELECTOR)
            if await user_score_element.first.is_visible(timeout=1_000):
                user_score = await user_score_element.first.text_content()
            else:
                user_score = "Ще не має рейтингу"
            user_registration = await page.locator(USER_REGISTRATION_SELECTOR).first.text_content()
            user_last_seen_element = page.locator(USER_LAST_SEEN_SELECTOR)
            if await user_last_seen_element.first.is_visible(timeout=100):
                user_last_seen = await page.locator(USER_LAST_SEEN_SELECTOR).first.text_content()
            else:
                user_last_seen = None

            # Location
            map_overlay = page.locator(MAP_OVERLAY_SELECTOR)
            location_section = map_overlay.locator("..")
            location_parts = await location_section.locator("svg + div *").all_text_contents()
            location = " ".join(loc.strip() for loc in location_parts if loc)

            # Extracting images
            block_with_photos = page.locator(BLOCK_WITH_PHOTO_SELECTOR)
            if await block_with_photos.first.is_visible(timeout=1_000):
                img_elements = await block_with_photos.locator("img").all()
                img_urls_list = [await img.get_attribute("src") for img in img_elements if await img.get_attribute("src")]
            else:
                img_urls_list = ["Ad does not have photos"]

            # Extracting tags and description
            ad_tags_element = page.locator(AD_TAGS_SELECTOR)
            if await ad_tags_element.first.is_visible(timeout=1_000):
                ad_tags = await page.locator(AD_TAGS_SELECTOR).all_text_contents()
            else:
                ad_tags = ["Ad doesnt have tags"]

            description_parts = await page.locator(DESCRIPTION_PARTS_SELECTOR).all_text_contents()
            description = " ".join(part.strip() for part in description_parts if part)

            # Extracting ad ID and view counter
            ad_id = await page.locator(AD_ID_SELECTOR).first.text_content()

            ad_view_counter_element = page.locator(AD_VIEW_COUNTER_SELECTOR)
            if await ad_view_counter_element.is_visible(timeout=3_000):
                ad_view_counter = await page.locator(AD_VIEW_COUNTER_SELECTOR).text_content()
            else:
                ad_view_counter = "Ad doesnt have view"

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

            phone_number_element = page.locator(CONTACT_PHONE_SELECTOR)
            if await phone_number_element.first.is_visible(timeout=2_000):
                phone_number = await page.locator(CONTACT_PHONE_SELECTOR).first.text_content()
            else:
                phone_number = "N/A"

            item["phone_number"] = phone_number if phone_number else None
            self.logger.info("Phone is %s", phone_number)
            # Save data
            yield item
            await page.close()
            self.logger.info("Page closed")
        except Exception as e:
            self.logger.error(f"Error in parse_ad: {e}")
            await page.close()
            self.logger.info("Page closed after exception %s", e)
            raise

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
