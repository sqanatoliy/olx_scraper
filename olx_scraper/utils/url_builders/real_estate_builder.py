from urllib.parse import urlencode

from base_builder import BaseUrlBuilder


class RealEstateUrlBuilder(BaseUrlBuilder):
    """
    URL generator for real estate (nedvizhimost).
    """

    # Доступні типи нерухомості
    PROPERTY_TYPES = {
        "kvartiry": "kvartiry",
        "komnaty": "komnaty",
        "doma": "doma",
        "posutochno": "posutochno-pochasovo",
        "zemlya": "zemlya",
        "kommercheskaya": "kommercheskaya-nedvizhimost",
        "garazhy": "garazhy-parkovki",
        "za-rubezhom": "nedvizhimost-za-rubezhom",
    }

    # Доступні підкатегорії (тип угоди)
    DEAL_TYPES = {
        "prodazha-kvartir": "prodazha-kvartir",
        "arenda-kvartir": "dolgosrochnaya-arenda-kvartir",

        "prodazha-komnat": "prodazha-komnat",
        "arenda-komnat": "dolgosrochnaya-arenda-komnat",

        "prodazha-domov": "prodazha-domov",
        "arenda-domov": "arenda-domov",

        "posutochno-doma": "posutochno-pochasovo-doma",
        "posutochno-kvartiry": "posutochno-pochasovo-kvartiry",
        "posutochno-komnaty": "posutochno-pochasovo-komnaty",
        "posutochno-oteli": "posutochno-pochasovo-oteli",
        "posutochno-khostely": "posutochno-pochasovo-khostely",
        "posutochno-predlozheniya-turoperatorov": "predlozheniya-turoperatorov",

        "arenda-zemli": "arenda-zemli",
        "prodazha-zemli": "prodazha-zemli",

        "prodazha-kommercheskoy-nedvizhimosti": "prodazha-kommercheskoy-nedvizhimosti",
        "arenda-kommercheskoy-nedvizhimosti": "arenda-kommercheskoy-nedvizhimosti",
        "kovorkingi": "kovorkingi",
        "arenda-garazhey-parkovok": "arenda-garazhey-parkovok",
        "prodazha-garazhey-parkovok": "prodazha-garazhey-parkovok",
    }

    def __init__(self, subcategory_1=None, subcategory_2=None, location=None, filters_dict=None):
        """
        :param subcategory_1: Тип нерухомості (kvartiry, doma, garazhi, тощо).
        :param subcategory_2: Тип угоди (prodazha або arenda).
        :param location: Локація (наприклад, 'ivano-frankovsk').
        """
        super().__init__("nedvizhimost", filters_dict)
        self.property_type = self.PROPERTY_TYPES.get(subcategory_1)  # Може бути `None`, якщо не вказано
        self.deal_type = self.DEAL_TYPES.get(subcategory_2)  # Може бути `None`, якщо не вказано
        self.location = location

    def apply_default_filters(self):
        """Задає стандартні фільтри для нерухомості"""
        if "currency" not in self.filters:
            self.filters["currency"] = "UAH"

    def set_total_area_range(self, min_area=None, max_area=None):
        """Filter by object area"""
        if min_area:
            self.filters["search[filter_float_total_area:from]"] = min_area
        if max_area:
            self.filters["search[filter_float_total_area:to]"] = max_area
        return self

    def build_url(self, page=1):
        """Forms URLs for real estate based on category, subcategory, deal type, location, and filters."""

        # Initial URL - only  `nedvizhimost`
        base_url = self.BASE_URL + self.category + "/"

        # Add the type of real estate, if it is specified
        if self.property_type:
            base_url += f"{self.property_type}/"

        # add subcategory if exist
        if self.deal_type:
            base_url += f"{self.deal_type}/"

        # Add the location, if it is specified
        if self.location:
            base_url += f"{self.location}/"

        base_url += self.format_keyword()

        self.set_page(page)

        return f"{base_url}?{urlencode(self.filters, doseq=True)}" if self.filters else base_url


if __name__ == "__main__":

    builder = RealEstateUrlBuilder(subcategory_1="posutochno", subcategory_2="posutochno-kvartiry", location="kiev", filters_dict={"q": "з опаленням"})
    print(builder.build_url(page=1))
