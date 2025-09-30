from urllib.parse import urlencode

from .base_builder import BaseUrlBuilder


class TransportUrlBuilder(BaseUrlBuilder):
    """
    URL generator for the transport section.
    """

    TRANSPORT_TYPES = {
        "legkovye-avtomobili": "legkovye-avtomobili",
        "gruzovye-avtomobili": "gruzovye-avtomobili",
        "avtobusy": "avtobusy",
        "moto": "moto",
        "spetstehnika": "spetstehnika",
        "selhoztehnika": "selhoztehnika",
        "vodnyy-transport": "vodnyy-transport",
        "avtomobili-iz-polshi": "avtomobili-iz-polshi",
        "pritsepy-doma-na-kolesah": "pritsepy-doma-na-kolesah",
        "gruzoviki-i-spetstehnika-iz-polshi": "gruzoviki-i-spetstehnika-iz-polshi",
        "drugoy-transport": "drugoy-transport",
    }

    SUB_CATEGORY_TRANSPORT = {
        "acura": "acura",
        "alfa_romeo": "alfa_romeo",
        "aston_martin": "aston_martin",
        "audi": "audi",
        "bentley": "bentley",
        "bmw": "bmw",
        "bmw_alpina": "bmw_alpina",
        "brilliance": "brilliance",
        "buick": "buick",
        "byd": "byd",
        "cadillac": "cadillac",
        "chana": "chana",
        "chery": "chery",
        "chevrolet": "chevrolet",
        "chrysler": "chrysler",
        "citroen": "citroen",
        "dacia": "dacia",
        "dadi": "dadi",
        "daewoo": "daewoo",
        "daihatsu": "daihatsu",
        "dodge": "dodge",
        "faw": "faw",
        "ferrari": "ferrari",
        "fiat": "fiat",
        "ford": "ford",
        "geely": "geely",
        "gmc": "gmc",
        "great_wall": "great_wall",
        "groz": "groz",
        "honda": "honda",
        "hummer": "hummer",
        "hyundai": "hyundai",
        "infiniti": "infiniti",
        "isuzu": "isuzu",
        "iveco": "iveco",
        "jac": "jac",
        "jaguar": "jaguar",
        "jeep": "jeep",
        "kia": "kia",
        "lamborghini": "lamborghini",
        "lancia": "lancia",
        "land_rover": "land_rover",
        "lexus": "lexus",
        "lifan": "lifan",
        "lincoln": "lincoln",
        "lotus": "lotus",
        "maserati": "maserati",
        "maybach": "maybach",
        "mazda": "mazda",
        "mclaren": "mclaren",
        "mercedes_benz": "mercedes_benz",
        "mercury": "mercury",
        "mg": "mg",
        "mini": "mini",
        "mitsubishi": "mitsubishi",
        "nissan": "nissan",
        "oldsmobile": "oldsmobile",
        "opel": "opel",
        "peugeot": "peugeot",
        "polestar": "polestar",
        "pontiac": "pontiac",
        "porsche": "porsche",
        "proton": "proton",
        "ram": "ram",
        "ravon": "ravon",
        "renault": "renault",
        "rolls_royce": "rolls_royce",
        "roewe": "roewe",
        "rover": "rover",
        "saab": "saab",
        "samand": "samand",
        "samsung": "samsung",
        "seat": "seat",
        "shelby": "shelby",
        "skoda": "skoda",
        "smart": "smart",
        "ssangyong": "ssangyong",
        "subaru": "subaru",
        "suzuki": "suzuki",
        "tata": "tata",
        "tesla": "tesla",
        "toyota": "toyota",
        "volkswagen": "volkswagen",
        "volvo": "volvo",
        "wartburg": "wartburg",
        "zx": "zx",
        "bogdan": "bogdan",
        "vaz": "vaz",
        "gaz": "gaz",
        "zaz": "zaz",
        "izh": "izh",
        "luaz": "luaz",
        "moskvich_azlk": "moskvich_azlk",
        "raf": "raf",
        "uaz": "uaz",
        "drugie": "drugie",
    }

    def __init__(
        self, subcategory_1=None, subcategory_2=None, location=None, filters_dict=None
    ):
        super().__init__("transport", filters_dict)
        self.transport_type = self.TRANSPORT_TYPES.get(subcategory_1)
        self.transport_sub_category = (
            self.SUB_CATEGORY_TRANSPORT.get(subcategory_2)
            if subcategory_1 == "legkovye-avtomobili"
            else None
        )
        self.location = location

    def apply_default_filters(self):
        """Set standard filters for transport"""
        if "currency" not in self.filters:
            self.filters["currency"] = "UAH"

    def set_mileage_range(self, min_mileage=None, max_mileage=None):
        """Filter by mileage"""
        if min_mileage:
            self.filters["search[filter_float_motor_mileage_thou:from]"] = min_mileage
        if max_mileage:
            self.filters["search[filter_float_motor_mileage_thou:to]"] = max_mileage
        return self

    def build_url(self, page=1):
        """Generate URL for transport based on category, subcategory, location, and filters."""

        # Initial URL - only `transport`
        base_url = self.BASE_URL + self.category + "/"

        if self.transport_type:
            base_url += f"{self.transport_type}/"

        if self.transport_sub_category:
            base_url += f"{self.transport_sub_category}/"

        if self.location:
            base_url += f"{self.location}/"

        base_url += self.format_keyword()

        self.set_page(page)

        return (
            f"{base_url}?{urlencode(self.filters, doseq=True)}"
            if self.filters
            else base_url
        )


if __name__ == "__main__":
    builder = TransportUrlBuilder()
    builder1 = TransportUrlBuilder(subcategory_1="legkovye-avtomobili")
    builder2 = TransportUrlBuilder(
        subcategory_1="legkovye-avtomobili",
        subcategory_2="acura",
        location="kiev",
        filters_dict={"q": "не бита"},
    )
    builder3 = TransportUrlBuilder(
        subcategory_1="legkovye-avtomobili", subcategory_2="acura"
    )
    builder3.set_mileage_range("1000", "50000")
    print(builder.build_url(page=1))
    print(builder1.build_url(page=1))
    print(builder2.build_url(page=1))
    print(builder3.build_url(page=1))
