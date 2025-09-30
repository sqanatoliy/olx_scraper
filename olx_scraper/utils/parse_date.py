import re
import typing
from datetime import datetime, timedelta


def parse_date(input_str) -> str:
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
        full_date: str = yesterday.strftime(f"%d {months_uk[yesterday.month]} %Y р.")
    elif input_str.startswith("Онлайн в "):
        full_date: str = today.strftime(f"%d {months_uk[today.month]} %Y р.")
    elif input_str.startswith("Онлайн "):
        input_str = input_str[len("Онлайн ") :]
        match: re.Match[str] | None = re.match(
            r"(\d{1,2}) ([а-яіїє]+) (\d{4}) р\.", input_str
        )
        if not match:
            print(f"Некоректний формат дати: {input_str}")
            return ""
        day: str = match.group(1).zfill(2)
        month: str = match.group(2)
        year: str = match.group(3)
        if month not in months_uk.values():
            print(f"Некоректний місяць у даті: {month}")
        full_date = f"{day} {month} {year} р."
    else:
        match: re.Match[str] | None = re.match(
            r"(\d{1,2}) ([а-яіїє]+) (\d{4}) р\.", input_str
        )
        if not match:
            print(f"Некоректний формат дати: {input_str}")
        day: str | typing.Any = match.group(1).zfill(2)
        month: str | typing.Any = match.group(2)
        year: str = match.group(3)
        if month not in months_uk.values():
            print(f"Некоректний місяць у даті: {month}")
        full_date = f"{day} {month} {year} р."
    return full_date


if __name__ == "__main__":
    print(parse_date("Онлайн 13 травня 2024 р."))
