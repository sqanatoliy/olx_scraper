from urllib.parse import urlencode, urljoin, quote_plus
from abc import ABC, abstractmethod


class BaseUrlBuilder(ABC):
    """
    A base class for generating search URLs on OLX.
    """

    BASE_URL = "https://www.olx.ua/uk/"

    def __init__(self, category: str, filters_dict=None):
        """
        :param category: Основний розділ OLX, наприклад 'nedvizhimost', 'transport', 'uslugi'.
        :param filters_dict: Словник із фільтрами (наприклад, ціна, фото, валюта).
        """
        self.category = category
        self.filters = filters_dict if filters_dict else {}
        self.keyword = self.filters.pop("q", None)

    @abstractmethod
    def apply_default_filters(self):
        """
        A method that will be overridden in child classes to apply standard filters.
        """
        pass

    def format_keyword(self):
        """Formats the keyword `q-{keyword}/` (spaces are replaced by hyphens)"""
        if self.keyword:
            return f"q-{quote_plus(self.keyword.replace(' ', '-'))}/"
        return ""

    def set_page(self, page=1):
        """Sets the page number"""
        self.filters["page"] = page
        return self

    def build_url(self, page=1):
        """Generates a basic URL without subcategories"""
        self.set_page(page)
        base_url = urljoin(self.BASE_URL, self.category + "/")
        return (
            f"{base_url}?{urlencode(self.filters, doseq=True)}"
            if self.filters
            else base_url
        )
