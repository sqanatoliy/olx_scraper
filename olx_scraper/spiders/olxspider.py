import logging
import re
from datetime import datetime, timedelta
from typing import Iterator, AsyncGenerator, Any

import scrapy
from parsel import Selector
from scrapy.http import Response
from scrapy.selector.unified import SelectorList
from scrapy_playwright.page import PageMethod

from ..items import OlxScraperItem
from .playwright_helpers import (
    check_403_error,
    scroll_to_number_of_views,
    scroll_and_click_to_show_phone,
    wait_for_number_of_views,
)
from ..pipelines import PostgresPipeline

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
    'div[data-testid="ad-promotion-actions"] + div[data-testid="qa-advert-slot"] + div'
)
DESCRIPTION_PARTS_SELECTOR = 'div[data-cy="ad_description"] > div'
# Description section footer
FOOTER_BAR_SELECTOR = 'div[data-testid="ad-footer-bar-section"]'
AD_ID_SELECTOR = 'normalize-space(//div[@data-testid="ad-footer-bar-section"]/span)'
AD_VIEW_COUNTER_SELECTOR = 'span[data-testid="page-view-counter"]'


class OlxSpider(scrapy.Spider):
    """Scraper for olx.ua/list"""

    name = "olx"
    allowed_domains: list[str] = ["olx.ua"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.db_pipeline = None

    def open_spider(self, spider):
        """Get instance `PostgresPipeline`"""
        for pipeline in spider.crawler.engine.scraper.itemproc.pipelines:
            if isinstance(pipeline, PostgresPipeline):
                self.db_pipeline = pipeline
                break

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        """Scrapy passes a `crawler` to give access to the `settings`"""
        spider = super().from_crawler(crawler, *args, **kwargs)
        # Get value from settings.py
        spider.start_page = crawler.settings.getint("START_PAGE", 1)
        spider.end_page = crawler.settings.getint("END_PAGE", 6)
        spider.start_urls = [
            f"https://www.olx.ua/uk/list/?page={i}" for i in range(spider.start_page, spider.end_page + 1)
        ]
        return spider

    def start_requests(self) -> Iterator[scrapy.Request]:
        """Override start_requests to include Playwright meta"""
        for url in self.start_urls:
            self.logger.debug(f"Generating request for URL: {url}")
            yield scrapy.Request(
                url=url,
                callback=self.parse,
                meta={
                    "playwright": True,
                    "playwright_context": "new",
                    "playwright_context_kwargs": {
                        "ignore_https_errors": True,
                        "viewport": {"width": 1980, "height": 1020},
                        "locale": "uk-UA",
                        "timezone_id": "Europe/Kiev",
                        # "proxy": {
                        #     "server": "http://proxy.toolip.io:31114",
                        #     "username": "tl-d8582f18f76fecabd2f916e4bd0df4cf63c9f54cd0c1b3d14529591b9ffac8c7-country-us-session-c9166",
                        #     "password": "t6yqmxldm870",
                        # },
                    },
                    "playwright_page_methods": [
                        PageMethod(check_403_error, url, self),
                        PageMethod(
                            "wait_for_selector", AD_TITLE_URL_SELECTOR, timeout=10_000
                        ),
                    ],
                },
                errback=self.errback_close_page,
            )

    def parse(self, response: Response) -> Iterator[scrapy.Request]:
        """Get all urls"""
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
            # Check in the database through `PostgresPipeline`
            if self.db_pipeline and self.db_pipeline.is_ad_in_db(full_url):
                self.logger.info(f"Skipping already processed ad: {full_url}")
                continue
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
                    "item": item,
                    "playwright": True,
                    "playwright_include_page": True,
                    "playwright_context": "new",
                    "playwright_context_kwargs": {
                        "ignore_https_errors": True,
                        "viewport": {"width": 1980, "height": 1020},
                        "locale": "uk-UA",
                        "timezone_id": "Europe/Kiev",
                        # "proxy": {
                        #     "server": "http://proxy.toolip.io:31114",
                        #     "username": "tl-d8582f18f76fecabd2f916e4bd0df4cf63c9f54cd0c1b3d14529591b9ffac8c7-country-us-session-c9166",
                        #     "password": "t6yqmxldm870",
                        # },
                    },
                    "playwright_page_methods": [
                        PageMethod(check_403_error, full_url, self),
                        PageMethod(
                            scroll_to_number_of_views,
                            FOOTER_BAR_SELECTOR,
                            USER_NAME_SELECTOR,
                            DESCRIPTION_PARTS_SELECTOR,
                            self,
                        ),
                        PageMethod(
                            "wait_for_load_state",
                            "domcontentloaded",
                            timeout=10_000,
                        ),
                        PageMethod(
                            wait_for_number_of_views,
                            AD_VIEW_COUNTER_SELECTOR,
                            self,
                        ),
                    ],
                },
                errback=self.errback_close_page,
            )

    async def parse_ad(
            self, response: Response
    ) -> AsyncGenerator[OlxScraperItem, None]:
        """Processing the detailed page of the ad"""
        page: Any = response.meta["playwright_page"]
        try:
            item: OlxScraperItem = response.meta["item"]

            # Ad publication date
            ad_pub_date: str | None = (
                response.css(AD_PUB_DATE_SELECTOR).css("::text").get()
            )

            # User profile
            user_name: str | None = response.css(USER_NAME_SELECTOR).css("::text").get()
            user_score: str | None = (
                response.css(USER_SCORE_SELECTOR).css("::text").get()
            )
            user_registration: str | None = (
                response.css(USER_REGISTRATION_SELECTOR).css("::text").get()
            )
            user_last_seen: str | None = (
                response.css(USER_LAST_SEEN_SELECTOR).css("::text").get()
            )

            # Location
            map_overlay = response.css(MAP_OVERLAY_SELECTOR)
            location_section = map_overlay.xpath("..")
            location_parts: list[str] = location_section.css(
                "svg + div *::text"
            ).getall()
            location: str = " ".join(locat.strip() for locat in location_parts if locat)

            # block with urls on the photos
            block_with_photos = response.css(BLOCK_WITH_PHOTO_SELECTOR)
            # Get all src values from img tags
            img_urls_list: list[str] = []
            for div in block_with_photos[:]:
                img_srcs: list[str] = div.css("img::attr(src)").getall()
                img_urls_list.extend(img_srcs)

            # Announcement tags
            ad_tags: list[str | None] = (
                response.css(AD_TAGS_SELECTOR).css("*::text").getall()
            )
            # Announcement description
            description_parts: list[str] = (
                response.css(DESCRIPTION_PARTS_SELECTOR).css("::text").getall()
            )
            description: str = " ".join(
                part.strip() for part in description_parts if part
            )
            # Announcement ID
            ad_id: str | None = response.xpath(AD_ID_SELECTOR).get()
            ad_view_counter: str | None = (
                response.css(AD_VIEW_COUNTER_SELECTOR).css("::text").get()
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
            page_content: Any = await page.content()
            new_html = Selector(text=page_content)

            phone_number: str | None = (
                new_html.css(CONTACT_PHONE_SELECTOR).css("::text").get()
            )
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

    async def errback_close_page(self, failure) -> None:
        meta: Any = failure.request.meta
        if "playwright_page" in meta:
            page: Any = meta["playwright_page"]
            self.logger.error(f"Closing page due to error: {failure}")
            await page.close()
            self.logger.info("Page closed after exception")

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
