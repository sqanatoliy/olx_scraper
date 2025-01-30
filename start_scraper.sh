#!/bin/bash

export PATH="/usr/local/bin:/usr/bin:/bin:$PATH"

# Wait for PostgreSQL to be ready
/app/wait-for-postgres.sh db

# Run the Scrapy spider from right path
cd /app && /usr/local/bin/scrapy crawl olx >> /app/logs/scrapy.log 2>&1