"""
Модуль для взаємодії з Playwright у Scrapy.
Містить допоміжні функції для перевірки помилки 403,
паузи виконання скрипта, скролінгу та кліків на елементах сторінки.
"""
import scrapy
from playwright.async_api import Page
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from scrapy.exceptions import IgnoreRequest


async def check_403_error(page: Page, ad_link: str, spider: scrapy.Spider) -> None:
    """
    Перевіряє сторінку на наявність помилки 403 від CloudFront.

    Якщо на сторінці знайдено заголовок "403 ERROR", функція:
    - Виводить повідомлення в консоль.
    - Логує повідомлення з використанням scrapy_logger.
    - Очікує 45 секунд.
    - Закриває сторінку.
    - Піднімає виключення IgnoreRequest для виключення поточного запиту.

    :param spider: екземпляр scrapy.Spider
    :param page: Екземпляр Playwright Page.
    :param ad_link: URL оголошення для логування.
    :raises IgnoreRequest: Якщо виявлено блокування через CloudFront.
    """
    if await page.locator("h1", has_text="403 ERROR").count() > 0:
        print(f"===== Attention Blocked by CloudFront !!! URL: {ad_link} =====")
        spider.logger.warning("===== Attention 403 ERROR detected. Blocked by CloudFront Next request in 5 seconds URL: %s =====", ad_link)
        await page.wait_for_timeout(45_000)
        await page.close()
        raise IgnoreRequest(f"===== Blocked by CloudFront. URL: {ad_link} =====")


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
        await page.wait_for_selector(footer_bar_selector, timeout=20_000)
    except PlaywrightTimeoutError as err:
        spider.logger.error(
            "=== Tried to scroll into Number of Views but it's not displayed: %s ===", err)
        await page.close()
        return
    try:
        spider.logger.info(
            "----------------===== Start to scrolling into Number of Views =====-----------------"
        )
        await page.locator(footer_bar_selector).scroll_into_view_if_needed()
        await page.locator(user_name_selector).first.wait_for(timeout=10_000)
        await page.locator(description_parts_selector).wait_for(timeout=10_000)
        spider.logger.info(
            "----------------===== Page should have loaded =====-----------------"
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
        await page.wait_for_selector(ad_view_counter_selector, timeout=3_000)
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
        await page.locator(btn_show_phone_selector).wait_for(timeout=2_000)
    except PlaywrightTimeoutError as err:
        spider.logger.warning("===The 'Show phone' button is not displayed: %s ===", err)
        return
    await page.locator(btn_show_phone_selector).scroll_into_view_if_needed(
        timeout=1_000
    )
    spider.logger.info("=== End to scrolling into show phone button ===")
    await page.click(btn_show_phone_selector, timeout=5_000)
    spider.logger.info("=== The “Show phone” button was clicked ===")
    try:
        await page.locator(contact_phone_selector).last.wait_for(timeout=3_000)
        spider.logger.info("=== The phone has been displayed successfully ===")
    except PlaywrightTimeoutError:
        spider.logger.warning(
            "=== Phone did not display successfully after clicking the 'Show Phone' button ===")
        return
    return
