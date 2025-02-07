from urllib.parse import urlencode

from .base_builder import BaseUrlBuilder


class GeneralListUrlBuilder(BaseUrlBuilder):
    """
    URL generator for a general listing of ads  (list).
    """

    def __init__(self, location=None, filters_dict=None):
        """
        :param location: Локація (місто або область).
        :param filters_dict: Словник фільтрів для URL (без ключового слова, воно додається окремо).
        """
        super().__init__("list", filters_dict)
        self.location = location

    def apply_default_filters(self):
        """
        Standard filters for the general list of ads:
        - Sets the currency to UAH.
        """
        if "currency" not in self.filters:
            self.filters["currency"] = "UAH"

    def build_url(self, page=1):
        """
        Generates a URL for the list of ads with filters and a keyword in the correct format.
        """
        # Base URL (depends on location availability)
        base_url = f"{self.BASE_URL}{self.location}/" if self.location else self.BASE_URL + self.category + "/"
        base_url += self.format_keyword()
        self.set_page(page)
        return f"{base_url}?{urlencode(self.filters, doseq=True)}" if self.filters else base_url


if __name__ == "__main__":
    link_class = GeneralListUrlBuilder(location="lvov", filters_dict={"q": "thinkpad"})
    link_class.apply_default_filters()
    print(link_class.build_url())

    builder = GeneralListUrlBuilder()
    print(builder.build_url(page=1))
