# OLX Scraper

## ⚠️ Увага
Цей проєкт був виконаний в рамках тестового завдання і не має комерційної цінності. Використання на продакшені може вимагати додаткових налаштувань безпеки та стабільності.

---

## 📌 Опис проєкту
Цей скрапер використовує **Scrapy** та **чистий Playwright** для збору даних із заданої кількості сторінок оголошень на OLX. Він зберігає дані у PostgreSQL та підтримує багатопотокову обробку. Дозволяє здійснювати пошук за різними категоріями оголошень, забезпечує фільтрацію за ключовими словами, локацією є можливість налаштувати інші фільтри присутні на OLX.

---

##  Особливості

- Скрапінг за категорією, локацією та ключовими словами

- Підтримка підкатегорій для нерухомості та транспорту

- Взяття номерів телефонів

- Зберігання у PostgreSQL

- Docker-ized: підтримка docker-compose

- Автоматичні дампи бази щодоби

- Запуск скрапера щогодини

---


## 📥 Створення нового проєкту
### 1️⃣ **Клонування репозиторію**
```bash
git clone https://github.com/sqanatoliy/olx_scraper.git
cd olx_scraper
```

### 2️⃣ **Створення віртуального середовища та встановлення залежностей**
```bash
python -m venv venv
source venv/bin/activate  # Linux/MacOS
venv\Scripts\activate    # Windows
pip install -r requirements.txt
```

---

## 🚀 Локальний запуск

### 1️⃣ **Заповнення `.env.local`**
Перед запуском потрібно створити файл `.env.local` та заповнити його:
```
POSTGRES_USER=your_user
POSTGRES_PASSWORD=your_password
POSTGRES_DB=your_database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
OLX_EMAIL=your_email@example.com
OLX_PASSWORD=your_password
```

### 2️⃣ **Запуск скрапера**

Перед запуском підготуйте .env з вашими даними.

Приклад запиту для категорії *Транспорт* підкатегорії *Легкові автомобілі* та марки авто *Volksvagen* Буде оброблена одна (перша сторінка оголошень за даними фільтрами)

```bash
scrapy crawl olx -a category=transport -a subcategory_1=legkovye-avtomobili -a subcategory_2=volkswagen -a end_page=1 -o ads.json
```

---

## 🐳 Запуск у Docker

### 1️⃣ **Заповнення `.env`**
```bash
POSTGRES_USER=your_user
POSTGRES_PASSWORD=your_password
POSTGRES_DB=your_database
POSTGRES_HOST=db
POSTGRES_PORT=5432
OLX_EMAIL=your_email@example.com
OLX_PASSWORD=your_password
```

### 2️⃣ **Запуск у контейнері**
```bash
docker-compose up --build
```

Це запустить **скрапер + PostgreSQL** у Docker-контейнерах.

### 3️⃣ **Зупинка контейнерів**
```bash
docker-compose down
```

---

## 📌 Використання чистого Playwright
У цьому проєкті **не використовується Scrapy-Playwright**, а замість цього **чистий Playwright**:
- **Один браузер та контекст для всіх запитів** (зменшує використання пам’яті).
- **Підтримка авторизації через `storage_state.json`**.
- **Гнучкіший контроль над Playwright** (можливість налаштувати затримки, антидетект).

---

## 🔥 Багатопотоковий режим
Щоб запустити скрапер у багатопотоковому режимі, потрібно змінити параметр у `settings.py`:
```python
CONCURRENT_REQUESTS = 8  # Кількість одночасних запитів
```

> **⚠️ Застереження:** Велика кількість потоків може призвести до блокування вашої IP-адреси.

---

## 🌍 Використання проксі
На даний момент у проєкті **не налаштовані проксі**, що означає:
- OLX може заблокувати вашу IP-адресу після кількох сотень запитів.

---

## ⚙️ Конфігурація скрапінгу
У `settings.py` ви можете змінити кількість сторінок для збору:
```python
START_PAGE = 1
END_PAGE = 5  # Кількість сторінок для скрапінгу
```

---

## 📋 Вимоги, які виконує цей проєкт:

    ✅ Збирає посилання на оголошення з **перших 5 сторінок** OLX.
    ✅ Зберігає дані в **PostgreSQL**, без оновлення змінених оголошень.
    ✅ Уникає **дублікатів** у базі.
    ✅ Логування **5 файлів по 1 ГБ**.
    ✅ **Docker-розгортання через `docker-compose`**.
    ✅ Щоденні **дампи бази о 12:00 за Київським часом** у `dumps/`.
    ✅ Запуск скрапера **щогодини**.

---

## 📌 Важливі моменти
- **Використовується авторизація через Playwright**.
- **Для роботи без блокування потрібні проксі**.
- **Скрапер зберігає сесію через `storage_state.json`**, що дозволяє уникати повторного входу.

---

## 🔧 Майбутні покращення
- ✅ Додати **автоматичну ротацію проксі**.
- ✅ Оптимізувати **видобуток номерів телефону**.


🚀 **Проєкт готовий до роботи та розширення!**

