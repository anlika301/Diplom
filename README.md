# ETL-пайплайны для данных приёмной кампании

Дипломный проект. Два ETL-пайплайна для обработки данных поступления в университет — бакалавриат и магистратура. Данные проходят через 4 слоя: STG → ODS → DDS → MART. Оркестрация через Apache Airflow.

БД — PostgreSQL (Supabase).

## Структура

```
etl_bak_modular/   — бакалавриат
etl_mag_modular/   — магистратура
airflow/dags/      — DAG для запуска обоих пайплайнов
data/              — сюда кладутся исходные файлы (не в git)
```

## Запуск

Создать `.env.bak` и `.env.mag` по шаблону:

```env
DB_HOST=...
DB_PORT=5432
DB_NAME=postgres
DB_USER=...
DB_PASSWORD=...
```

Применить SQL-миграции из `etl_bak_modular/sql/` и `etl_mag_modular/sql/` по порядку номеров.

Запуск вручную:

```bash
cd etl_bak_modular
python3 main.py --layer all --run
```

```bash
cd etl_mag_modular
python3 main.py --layer all --run
```

Без `--run` — dry-run, в БД ничего не пишется.

## Airflow

```bash
docker compose -p dwh-airflow -f docker-compose.airflow.yml up -d
```

Веб-интерфейс: `http://localhost:8080` (airflow / airflow)

DAG называется `etl_dwh_combined`.
