from typing import Optional
from .url_builders.general_list_builder import GeneralListUrlBuilder
from .url_builders.real_estate_builder import RealEstateUrlBuilder
from .url_builders.transport_builder import TransportUrlBuilder


class UrlBuilderFactory:
    """
    A factory for creating a suitable URL generator based on a category.
    """

    BUILDERS: dict[str, type] = {
        "list": GeneralListUrlBuilder,
        "nedvizhimost": RealEstateUrlBuilder,
        "transport": TransportUrlBuilder,
    }

    @staticmethod
    def get_builder(
        category,
        location=None,
        subcategory_1=None,
        subcategory_2=None,
        filters_dict=None,
    ):
        """Get URL generator"""
        builder_class = UrlBuilderFactory.BUILDERS.get(category)
        if not builder_class:
            raise ValueError(f"❌ Немає генератора для категорії: {category}")

        # `GeneralListUrlBuilder` не підтримує `subcategory_1` і `subcategory_2`
        if category == "list":
            return builder_class(location=location, filters_dict=filters_dict)

        # Для `RealEstateUrlBuilder` та `TransportUrlBuilder` передаємо підкатегорії
        return builder_class(
            location=location,
            subcategory_1=subcategory_1,
            subcategory_2=subcategory_2,
            filters_dict=filters_dict,
        )
