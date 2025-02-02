"""
Модуль для взаємодії з Playwright у Scrapy.
Містить допоміжні функції для перевірки помилки 403,
паузи виконання скрипта, скролінгу та кліків на елементах сторінки.
"""
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

import scrapy
from decouple import config
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright, Page, BrowserContext

# Data for OLX Login
OLX_URL = "https://www.olx.ua/"
OLX_EMAIL = config("OLX_EMAIL")
OLX_PASSWORD = config("OLX_PASSWORD")

# path to state.json
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
STATE_FILE = PROJECT_ROOT / "state.json"

# Check that state.json exist else None
storage_state_path = str(STATE_FILE) if STATE_FILE.exists() else None


async def check_403_error(page: Page, ad_link: str, spider: scrapy.Spider, timeout: int = 30_000) -> None:
    """
    Перевіряє сторінку на наявність помилки 403 від CloudFront.

    Якщо на сторінці знайдено заголовок "403 ERROR", функція:
    логує повідомлення.
    очікує за замовчуванням 30 секунд.
    закриває сторінку.
    піднімає виключення.

    :param spider: екземпляр scrapy.Spider
    :param page: Екземпляр Playwright Page.
    :param ad_link: URL оголошення для логування.
    :param timeout: Час очікування перед закриттям сторінки
    :raises: Якщо виявлено блокування через CloudFront.
    """
    if await page.locator("h1", has_text="403 ERROR").count() > 0:
        print(f"===== Attention Blocked by CloudFront !!! URL: {ad_link} =====")
        spider.logger.warning(f"===== Attention 403 ERROR detected. Blocked by CloudFront Next request in {timeout} seconds URL: %s =====", ad_link)
        await page.wait_for_timeout(timeout)
        await page.close()
        raise f"===== Blocked by CloudFront. URL: {ad_link} ====="


async def page_pause(page: Page, spider: scrapy.Spider) -> None:
    """
    Призупиняє виконання сторінки за допомогою Playwright.

    Логує повідомлення про паузу сторінки та викликає функцію page.pause().

    :param page: Екземпляр Playwright Page.
    :param spider: екземпляр scrapy.Spider
    """
    spider.logger.info("===== Page on Pause ======")
    await page.pause()


async def scroll_to_number_of_views(
        page: Page,
        footer_bar_selector: str,
        user_name_selector: str,
        description_parts_selector: str,
        spider: scrapy.Spider
) -> None:
    """
    Скролить сторінку до певних елементів, що містять інформацію (наприклад, кількість переглядів).

    Функція виконує наступне:
    - Очікує появи елемента, що відповідає селектору футер-бару.
    - Якщо селектор футер-бару не з’являється, логує помилку, закриває сторінку та повертається.
    - Скролить до елемента футер-бару.
    - Очікує появи елементів з user_name та description_parts.
    - Логує успішне завантаження сторінки.

    :param page: Екземпляр Playwright Page.
    :param footer_bar_selector: Селектор для елемента футер-бару.
    :param user_name_selector: Селектор для елемента, що містить ім'я користувача.
    :param description_parts_selector: Селектор для елементів опису оголошення.
    :param spider: екземпляр scrapy.Spider
    """
    try:
        await page.wait_for_selector(footer_bar_selector, timeout=10_000)
    except PlaywrightTimeoutError as err:
        spider.logger.error(
            "=== Footer bar selector it's not displayed: %s ===", err)
        await page.close()
        return
    try:
        spider.logger.info(
            "-----===== Start to scrolling into Number of Views =====-----"
        )
        await page.locator(footer_bar_selector).scroll_into_view_if_needed()
        await page.locator(user_name_selector).first.wait_for(timeout=5_000)
        await page.locator(description_parts_selector).wait_for(timeout=5_000)
        spider.logger.info(
            "-----===== Page should have loaded =====-----"
        )
    except PlaywrightTimeoutError as err:
        spider.logger.error("=== Failed to get elements User Name, Description: %s ===", err)


async def wait_for_number_of_views(
        page: Page,
        ad_view_counter_selector: str,
        spider: scrapy.Spider,
) -> None:
    """
    Очікує на відображення кількості переглядів.

    Функція виконує наступне:
    - Очікує появи елемента, що відповідає кількість переглядів.

    :param page: Екземпляр Playwright Page.
    :param ad_view_counter_selector: Селектор для кількості переглядів.
    :param spider: екземпляр scrapy.Spider
    """
    try:
        await page.wait_for_selector(ad_view_counter_selector, timeout=500)
    except PlaywrightTimeoutError as err:
        spider.logger.warning(
            "=== The expectation for the number of views was not successful: %s ===", err)
        return
    spider.logger.info("=== Number of views received ===")
    return


async def scroll_and_click_to_show_phone(
        page: Page,
        btn_show_phone_selector: str,
        contact_phone_selector: str,
        spider: scrapy.Spider,
) -> None:
    """
    Скролить сторінку до кнопки "Показати телефон" та виконує клік по ній.

    Функція виконує наступні дії:
    - Логує початок операції скролінгу до кнопки.
    - Очікує появи кнопки за вказаним селектором.
    - Якщо кнопка не з’являється у встановлений час, логує повідомлення та повертається.
    - Скролить до кнопки, логує завершення скролінгу та виконує клік по кнопці.
    - Очікує появи елемента з контактним телефоном.
    - Логує успішне відображення телефону або повідомляє про невдалу спробу.

    :param page: Екземпляр Playwright Page.
    :param btn_show_phone_selector: Селектор для кнопки "Показати телефон".
    :param contact_phone_selector: Селектор для елемента, що містить контактний телефон.
    :param spider: екземпляр scrapy.Spider
    :return: None
    """
    try:
        spider.logger.info("=== Start to scrolling into show phone button ===")
        await page.locator(btn_show_phone_selector).wait_for(timeout=100)
    except PlaywrightTimeoutError as err:
        spider.logger.warning("===The 'Show phone' button is not displayed: %s ===", err)
        return
    await page.locator(btn_show_phone_selector).scroll_into_view_if_needed(
        timeout=2_000
    )
    spider.logger.info("=== End to scrolling into show phone button ===")
    await page.click(btn_show_phone_selector, timeout=2_000)
    spider.logger.info("=== The “Show phone” button was clicked ===")
    try:
        await page.locator(contact_phone_selector).last.wait_for(timeout=2_000)
        spider.logger.info("=== The phone has been displayed successfully ===")
    except PlaywrightTimeoutError:
        spider.logger.warning(
            "=== Phone did not display successfully after clicking the 'Show Phone' button ===")
        return
    return


# LOGIN OLX

# this context for authentication testing
@asynccontextmanager
async def new_context():
    """A new context that is needed either to test the login_olx function,
    or to manually save the auth state of state.json.
    The file will be saved to the root project directory
    then you can add it to the context when performing scraping"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-gpu",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ]
        )
        context: BrowserContext = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            java_script_enabled=True,
            timezone_id="Europe/Kiev",
            locale="uk-UA",
            extra_http_headers={
                "Accept-Language": "uk-UA,uk;q=0.9",
                "Referer": "https://www.olx.ua/",
            },
            storage_state=storage_state_path,
        )
        try:
            yield context
        finally:
            await browser.close()


async def login_olx(
        context: BrowserContext,
        olx_url: str,
        olx_email: str, olx_password: str,
        spider: scrapy.Spider = None,
) -> None:
    """Logs in to OLX using Playwright and saves the session"""
    page = await context.new_page()
    await page.evaluate("navigator.webdriver = undefined")
    await page.goto(olx_url, wait_until="domcontentloaded")
    # Check login status
    user_button = page.locator('h5[data-testid="topbar-dropdown-header"]')
    try:
        await user_button.wait_for(state="attached", timeout=5_000)
        if spider:
            spider.logger.info("✅ Авторизація успішно виконана з state.json файлу!")
        else:
            print("✅ Авторизація успішно виконана з state.json файлу!")
    except PlaywrightTimeoutError:

        try:
            await page.click('a[data-cy="myolx-link"]')
            await page.locator('#username').press_sequentially(olx_email, delay=100)
            await page.locator('#password').press_sequentially(olx_password, delay=100)
            await page.click('button[data-testid="login-submit-button"]')

            await user_button.wait_for(state="attached", timeout=10_000)
            if spider:
                spider.logger.info("✅ Авторизація успішно виконана через форму авторизації!")
            else:
                print("✅ Авторизація успішно виконана через форму авторизації!")

        except PlaywrightTimeoutError:
            if spider:
                spider.logger.warning("❌ Не вдалося авторизуватися!")
            else:
                print("❌ Не вдалося авторизуватися!")

    finally:
        # Save browser state
        await context.storage_state(path=STATE_FILE)
        await page.close()


# Get the context for testing and login
async def main():
    async with new_context() as context:
        await login_olx(context, OLX_URL, OLX_EMAIL, OLX_PASSWORD)


if __name__ == "__main__":
    asyncio.run(main())
