# Use the official Python image as a base
FROM python:3.11-slim

# Set env for Playwright
ENV PLAYWRIGHT_BROWSERS_PATH=/root/.cache/ms-playwright

# Set the working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    postgresql-client \
    cron \
    && rm -rf /var/lib/apt/lists/*

# Copy wait-for-postgres script
COPY wait-for-postgres.sh /app/wait-for-postgres.sh
RUN chmod +x /app/wait-for-postgres.sh

# Copy create db dump script
COPY dump_postgres.sh /app/dump_postgres.sh
RUN chmod +x /app/dump_postgres.sh

# Copy start_scraper script
COPY start_scraper.sh /app/start_scraper.sh
RUN chmod +x /app/start_scraper.sh

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright and its dependencies
RUN pip install playwright
RUN playwright install chromium --with-deps

# Copy the project files
COPY . .

# Create the dumps directory
RUN mkdir -p /app/dumps

RUN env >> /etc/environment

# create logfile before start cron
RUN touch /app/dumps/cron.log && chmod 777 /app/dumps/cron.log

# Add a cron job for database dump (daily at 12:00 Kyiv time)
RUN echo "0 15 * * * /bin/bash /app/dump_postgres.sh >> /app/dumps/cron.log 2>&1" > /etc/cron.d/db_dump

# Add a cron job for Scrapy execution every hour
RUN echo "0 * * * * /bin/bash /app/start_scraper.sh >> /var/log/cron.log 2>&1" > /etc/cron.d/scraper_cron

# Set permissions and apply crontab
RUN chmod 0644 /etc/cron.d/db_dump /etc/cron.d/scraper_cron && cat /etc/cron.d/db_dump /etc/cron.d/scraper_cron | crontab -

# Run cron and keep the container alive
ENTRYPOINT ["/bin/bash", "-c", "printenv | grep POSTGRES >> /etc/environment && cron -f && tail -f /app/dumps/cron.log"]
