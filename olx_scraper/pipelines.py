# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from itemadapter import ItemAdapter

import psycopg2
from itemadapter import ItemAdapter


class OlxScraperPipeline:
    def process_item(self, item, spider):
        return item


class PostgresPipeline:
    def __init__(self, postgres_uri, postgres_db, postgres_user, postgres_password):
        self.postgres_uri = postgres_uri
        self.postgres_db = postgres_db
        self.postgres_user = postgres_user
        self.postgres_password = postgres_password
        self.conn = None
        self.cursor = None

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            postgres_uri=crawler.settings.get("POSTGRES_URI"),
            postgres_db=crawler.settings.get("POSTGRES_DB"),
            postgres_user=crawler.settings.get("POSTGRES_USER"),
            postgres_password=crawler.settings.get("POSTGRES_PASSWORD"),
        )

    def open_spider(self, spider):
        try:
            spider.logger.info("Opening PostgreSQL pipeline.")
            self.conn = psycopg2.connect(
                host=self.postgres_uri,
                dbname=self.postgres_db,
                user=self.postgres_user,
                password=self.postgres_password
            )
            self.cursor = self.conn.cursor()
            # Create table if it doesn't exist
            self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS ads (
                ad_id VARCHAR(255) PRIMARY KEY,
                title TEXT,
                price TEXT,
                user_name TEXT,
                phone_number TEXT,
                user_score TEXT,
                user_registration TEXT,
                user_last_seen TEXT,
                ad_view_counter TEXT,
                location TEXT,
                ad_pub_date TEXT,
                url TEXT,
                description TEXT,
                ad_tags TEXT[],
                img_src_list TEXT[]
            )
            """)
            self.conn.commit()
        except psycopg2.Error as e:
            spider.logger.error(f"Error connecting to PostgreSQL: {e}")
            raise

    def close_spider(self, spider):
        try:
            spider.logger.info("Closing PostgreSQL pipeline.")
            if self.cursor:
                self.cursor.close()
            if self.conn:
                self.conn.close()
        except psycopg2.Error as e:
            spider.logger.error(f"Error closing PostgreSQL connection: {e}")

    def is_ad_in_db(self, url):
        """Checks if the ad is in the database"""
        self.cursor.execute("SELECT EXISTS(SELECT 1 FROM ads WHERE url = %s)", (url,))
        return self.cursor.fetchone()[0]

    def process_item(self, item, spider):
        try:
            adapter = ItemAdapter(item)
            data = (
                adapter.get('ad_id'),
                adapter.get('title'),
                adapter.get('price'),
                adapter.get('user_name'),
                adapter.get('phone_number'),
                adapter.get('user_score'),
                adapter.get('user_registration'),
                adapter.get('user_last_seen'),
                adapter.get('ad_view_counter'),
                adapter.get('location'),
                adapter.get('ad_pub_date'),
                adapter.get('url'),
                adapter.get('description'),
                adapter.get('ad_tags'),
                adapter.get('img_src_list'),

            )

            # Efficiently insert data using execute_values
            self.cursor.execute("""
            INSERT INTO ads (ad_id, title, price, user_name, phone_number, user_score, user_registration, 
                             user_last_seen, ad_view_counter, location, ad_pub_date, url, description, ad_tags, img_src_list)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (ad_id) DO NOTHING
            """, data)

            self.conn.commit()
            spider.logger.info(f"Item with ID {adapter.get('ad_id')} saved successfully.")
            return item

        except psycopg2.Error as e:
            spider.logger.error(f"Error saving item to PostgreSQL: {e}")
            self.conn.rollback()
            raise

        except Exception as e:
            spider.logger.error(f"Unexpected error in process_item: {e}")
            raise
