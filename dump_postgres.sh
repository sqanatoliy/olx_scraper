#!/bin/bash

set -e  # Stop script if any command fails
export PATH="/usr/local/bin:/usr/bin:/bin:$PATH"

source /etc/profile

# Settings
DUMP_DIR="/app/dumps"
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
DUMP_FILE="${DUMP_DIR}/dump_${TIMESTAMP}.sql"

# Логування початку роботи скрипта
echo "[$(date +"%Y-%m-%d %H:%M:%S")] Running dump_postgres.sh..." >> /app/dumps/cron.log
echo "Checking environment variables..." >> /app/dumps/cron.log

# Переконуємось, що змінні середовища встановлені
if [[ -z "$POSTGRES_URI" || -z "$POSTGRES_DB" || -z "$POSTGRES_USER" || -z "$POSTGRES_PASSWORD" ]]; then
    echo "[$(date +"%Y-%m-%d %H:%M:%S")] ERROR: One or more required environment variables are missing!" >> /app/dumps/cron.log
    env | grep POSTGRES >> /app/dumps/cron.log
    exit 1
fi

echo "Using DB_HOST: $POSTGRES_URI, DB_NAME: $POSTGRES_DB, DB_USER: $POSTGRES_USER" >> /app/dumps/cron.log

# Переконуємось, що папка для дампів існує
mkdir -p "$DUMP_DIR"

# Виконуємо дамп бази
export PGPASSWORD=$POSTGRES_PASSWORD
pg_dump -h "$POSTGRES_URI" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -F c -f "$DUMP_FILE" >> /app/dumps/cron.log 2>&1

# Лог, якщо дамп успішний
if [ $? -eq 0 ]; then
    chmod 600 "$DUMP_FILE"
    echo "[$(date +"%Y-%m-%d %H:%M:%S")] DB dump saved: $DUMP_FILE" >> /app/dumps/cron.log
else
    echo "[$(date +"%Y-%m-%d %H:%M:%S")] ERROR: Failed to create DB dump!" >> /app/dumps/cron.log
fi

# Видаляємо старіші дампи, залишаючи тільки останні 7
find "$DUMP_DIR" -type f -printf "%T@ %p\n" | sort -nr | tail -n +8 | awk '{print $2}' | xargs rm -f
