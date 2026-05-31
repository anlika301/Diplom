# DWH: ETL-пайплайны для данных поступления (Бакалавриат + Магистратура)

Проект реализует 4-слойное хранилище данных (DWH) для обработки данных приёмной кампании университета. Два независимых ETL-пайплайна оркестрируются через Apache Airflow.

## Архитектура

**Слои DWH:**

| Слой | Описание |
|------|----------|
| **STG** (Staging) | Сырые данные из CSV/Excel, все поля TEXT, без изменений |
| **ODS** (Operational Data Store) | Типизированные, дедуплицированные данные |
| **DDS** (Detailed Data Store) | Нормализованная схема с историей изменений (SCD Type 2) |
| **MART** | Аналитические витрины для отчётности |

**Источники данных:**
- Бакалавриат (`stg_bak` → `ods_bak` → `dds_bak`): ~44 000 заявлений, ~57 000 баллов, ~7 000 договоров
- Магистратура (`stg_mag` → `ods_mag` → `dds_mag` → `mart_mag`): ~7 000 договоров, ~10 000 графиков платежей

## Структура проекта

```
├── airflow/
│   └── dags/
│       └── etl_combined_dag.py   # DAG для оркестрации обоих пайплайнов
│
├── data/
│   ├── bak/                      # CSV-файлы бакалавриата (не в git)
│   └── mag/                      # CSV/Excel-файлы магистратуры (не в git)
│
├── docs/                         # Документация и ER-диаграммы
│
├── etl_bak_modular/              # ETL-пайплайн бакалавриата
│   ├── config.py                 # Подключение к БД (.env.bak)
│   ├── extractors.py             # Чтение CSV и слоёв БД
│   ├── fetch.py                  # Загрузка файлов с сетевого диска
│   ├── loaders.py                # Запись в БД (upsert, SCD2)
│   ├── main.py                   # Оркестрация слоёв STG→ODS→DDS
│   ├── elt_schema.md             # Mermaid-диаграмма пайплайна
│   ├── sql/                      # DDL-скрипты по слоям
│   └── transformers/             # Трансформации STG, ODS, DDS
│
├── etl_mag_modular/              # ETL-пайплайн магистратуры
│   ├── config.py                 # Подключение к БД (.env.mag)
│   ├── extractors.py             # Чтение CSV и слоёв БД
│   ├── fetch.py                  # Загрузка файлов магистратуры
│   ├── loaders.py                # Запись в БД (upsert, SCD2)
│   ├── main.py                   # Оркестрация слоёв ODS→DDS→MART
│   ├── etl_schema.md             # Mermaid-диаграмма пайплайна
│   ├── sql/                      # DDL-скрипты по слоям
│   │   ├── 01_stg_mag.sql        # STG-схема
│   │   ├── 02_ods_mag.sql        # ODS-схема
│   │   ├── 03_dds_mag.sql        # DDS-схема с историей (SCD2)
│   │   ├── 04_mart_mag.sql       # Аналитические витрины
│   │   └── 05_fk_dds_mag.sql    # FK-связи (одноразовая миграция)
│   └── transformers/             # Трансформации ODS, DDS, MART
│
├── .env.bak                      # Credentials бакалавриата (не в git)
├── .env.mag                      # Credentials магистратуры (не в git)
├── .env.example                  # Шаблон переменных окружения
├── Dockerfile.airflow            # Docker-образ с зависимостями
├── docker-compose.airflow.yml    # Запуск Airflow (CeleryExecutor)
└── requirements.txt
```

---

## Установка и запуск с нуля

### Требования

- Python 3.10+
- Docker и Docker Compose
- PostgreSQL-база в Supabase (или другой PostgreSQL)

### 1. Клонировать репозиторий

```bash
git clone <repository-url>
cd <repository-folder>
```

### 2. Создать виртуальное окружение и установить зависимости

```bash
python3 -m venv .venv
source .venv/bin/activate        # macOS / Linux
# .venv\Scripts\activate         # Windows

pip install -r requirements.txt
```

### 3. Настроить подключение к базе данных

Создать два файла с credentials — для каждого пайплайна отдельно:

```bash
cp .env.example .env.bak
cp .env.example .env.mag
```

Заполнить реальными параметрами Supabase (или другого PostgreSQL):

```env
DB_HOST=aws-0-eu-west-1.pooler.supabase.com
DB_PORT=5432
DB_NAME=postgres
DB_USER=postgres.YOUR_PROJECT_ID
DB_PASSWORD=YOUR_SECURE_PASSWORD
```

> `.env.bak` и `.env.mag` добавлены в `.gitignore` — credentials не попадут в репозиторий.

### 4. Применить DDL-миграции в базе данных

Выполнить SQL-скрипты последовательно через Supabase SQL Editor или `psql`:

```bash
# Бакалавриат
psql $DATABASE_URL -f etl_bak_modular/sql/01_stg_bak.sql
psql $DATABASE_URL -f etl_bak_modular/sql/02_ods_bak.sql
psql $DATABASE_URL -f etl_bak_modular/sql/03_dds_bak.sql
psql $DATABASE_URL -f etl_bak_modular/sql/04_mart_bak.sql

# Магистратура
psql $DATABASE_URL -f etl_mag_modular/sql/01_stg_mag.sql
psql $DATABASE_URL -f etl_mag_modular/sql/02_ods_mag.sql
psql $DATABASE_URL -f etl_mag_modular/sql/03_dds_mag.sql
psql $DATABASE_URL -f etl_mag_modular/sql/04_mart_mag.sql

# FK-связи dds_mag (применять ПОСЛЕ первого запуска ETL, когда таблицы заполнены)
psql $DATABASE_URL -f etl_mag_modular/sql/05_fk_dds_mag.sql
```

Где `DATABASE_URL` — строка подключения вида `postgresql://user:password@host:5432/dbname`.

### 5. Разместить исходные данные

Положить файлы данных в соответствующие папки:

```
data/bak/   ← CSV-файлы бакалавриата (abitur_rows.csv, scores_rows.csv, ...)
data/mag/   ← CSV/Excel-файлы магистратуры (dogovor_rows.csv, grafics_rows.csv, ...)
```

> Папки `data/` в `.gitignore` — данные не хранятся в репозитории.

---

## Запуск ETL вручную

Для разовой проверки или отладки можно запустить пайплайн напрямую из командной строки.

```bash
# Бакалавриат — все слои (реальная запись)
cd etl_bak_modular
python3 main.py --layer all --run

# Магистратура — все слои (реальная запись)
cd etl_mag_modular
python3 main.py --layer all --run
```

**Флаги `main.py`:**

| Флаг | Описание |
|------|----------|
| `--layer all` | Запустить все слои (STG→ODS→DDS→MART) |
| `--layer stg` | Только Staging |
| `--layer ods` | Только ODS |
| `--layer dds` | Только DDS |
| `--layer mart` | Только MART (только для MAG) |
| `--run` | Реальная запись в БД (без флага — dry-run) |
| `--date YYYY-MM-DD` | Указать дату загрузки вручную |
| `--log-dir ./logs` | Сохранить лог в файл |

**Примеры:**

```bash
# Dry-run — посмотреть что будет загружено, без записи в БД
python3 main.py --layer all

# Загрузить только ODS с логом
python3 main.py --layer ods --run --log-dir ./logs

# Загрузить с конкретной датой
python3 main.py --layer all --run --date 2025-09-01
```

---

## Запуск через Apache Airflow

Airflow запускается в Docker с CeleryExecutor — MAG и BAK таски выполняются параллельно.

### 1. Собрать образ и инициализировать БД Airflow

```bash
# Сборка образа
docker compose -p dwh-airflow -f docker-compose.airflow.yml build

# Инициализация (создаёт таблицы, пользователя admin, переменные)
docker compose -p dwh-airflow -f docker-compose.airflow.yml up airflow-init
```

### 2. Запустить все сервисы

```bash
docker compose -p dwh-airflow -f docker-compose.airflow.yml up -d
```

Запускаются: `postgres` (метаданные Airflow), `redis` (брокер Celery), `airflow-scheduler`, `airflow-webserver`, `airflow-worker`.

### 3. Открыть веб-интерфейс

```
http://localhost:8080
Логин: airflow
Пароль: airflow
```

### 4. Запустить DAG

В интерфейсе найти DAG **`etl_dwh_combined`**, включить его (Toggle) и нажать **Trigger DAG**.

Порядок тасков:

```
start
├── fetch_mag → ods_mag → dds_mag → mart_mag
└── fetch_bak → ods_bak → dds_bak
```

### 5. Остановить Airflow

```bash
docker compose -p dwh-airflow -f docker-compose.airflow.yml down
```

---

## Переменные окружения

Оба `.env` файла используют одинаковую структуру:

| Переменная   | Описание                              |
|--------------|---------------------------------------|
| `DB_HOST`    | Хост PostgreSQL (Supabase pooler)     |
| `DB_PORT`    | Порт (5432 для прямого подключения)   |
| `DB_NAME`    | Имя базы данных (`postgres`)          |
| `DB_USER`    | Пользователь (`postgres.PROJECT_ID`)  |
| `DB_PASSWORD`| Пароль проекта                        |
