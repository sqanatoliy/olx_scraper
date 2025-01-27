# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class OlxScraperItem(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()

    ad_id = scrapy.Field()
    title = scrapy.Field()
    price = scrapy.Field()
    user_name = scrapy.Field()
    phone_number = scrapy.Field()
    user_score = scrapy.Field()
    user_registration = scrapy.Field()
    user_last_seen = scrapy.Field()
    ad_view_counter = scrapy.Field()
    location = scrapy.Field()
    ad_pub_date = scrapy.Field()
    url = scrapy.Field()
    description = scrapy.Field()
    ad_tags = scrapy.Field()
    img_src_list = scrapy.Field()

