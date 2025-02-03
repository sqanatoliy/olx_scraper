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
            spider.logger.info("📡 Opening PostgreSQL pipeline.")
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
            spider.logger.info("✅ Table checked or created.")
        except psycopg2.Error as e:
            spider.logger.error(f"❌ Error connecting to PostgreSQL: {e}")
            raise

    def close_spider(self, spider):
        try:
            spider.logger.info("Closing PostgreSQL pipeline.")
            if self.cursor:
                self.cursor.close()
            if self.conn:
                self.conn.close()
                spider.logger.info("✅ Connection successfully closed.")
        except psycopg2.Error as e:
            spider.logger.error(f"❌ Error closing PostgreSQL connection: {e}")

    def process_item(self, item, spider):
        try:
            adapter = ItemAdapter(item)

            ad_id = adapter.get('ad_id')
            if not ad_id:
                spider.logger.warning("⚠️ Item does not have a valid ad_id. Skipping insert.")
                return item

            # Checking if the ad_id is in the database
            self.cursor.execute("SELECT EXISTS(SELECT 1 FROM ads WHERE ad_id = %s)", (ad_id,))
            if self.cursor.fetchone()[0]:
                spider.logger.info(f"🔄 Item with ID {ad_id} already exists. Skipping insert.")
                return item

            data = (
                adapter.get('ad_id') or 'unknown',
                adapter.get('title') or 'No Title',
                adapter.get('price') or '0',
                adapter.get('user_name') or 'Anonymous',
                adapter.get('phone_number') or 'N/A',
                adapter.get('user_score') or 'N/A',
                adapter.get('user_registration') or 'Unknown',
                adapter.get('user_last_seen') or 'Unknown',
                adapter.get('ad_view_counter') or '0',
                adapter.get('location') or 'Unknown',
                adapter.get('ad_pub_date') or 'Unknown',
                adapter.get('url'),
                adapter.get('description') or 'No Description',
                adapter.get('ad_tags') or [],
                adapter.get('img_src_list') or [],

            )

            # Efficiently insert data using execute_values
            self.cursor.execute("""
            INSERT INTO ads (ad_id, title, price, user_name, phone_number, user_score, user_registration, 
                             user_last_seen, ad_view_counter, location, ad_pub_date, url, description, ad_tags, img_src_list)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (ad_id) DO NOTHING
            """, data)

            self.conn.commit()
            spider.logger.info(f"✅ Item with ID {adapter.get('ad_id')} saved successfully.")
            return item

        except psycopg2.Error as e:
            spider.logger.error(f"❌ Database error while saving item: {e}")
            self.conn.rollback()
            return item

        except Exception as e:
            spider.logger.error(f"❌ Unexpected error in process_item: {e}")
            return item
