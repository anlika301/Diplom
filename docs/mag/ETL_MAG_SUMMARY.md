# ETL MAG — Итоговое описание реализации

## Обзор

Реализован 4-слойный ETL-пайплайн для приёмной комиссии магистратуры (MAG) на базе **Supabase (PostgreSQL)**.  
Данные загружаются из 5 CSV-файлов в хранилище через слои STG → ODS → DDS → MART.

---

## Архитектура

```
CSV-файлы (5 шт.)
      ↓
  STG (Staging)        — сырые данные, TEXT-типы, ON CONFLICT DO NOTHING
      ↓
  ODS (Operational)    — типизированные данные, UPSERT по натуральному ключу
      ↓
  DDS (Distribution)   — нормализованная 3NF, измерения (SCD1) + факты (SCD2)
      ↓
  MART (Analytical)    — SQL-вьюхи для аналитики
```

---

## Источники данных

| Файл | Описание | Строк |
|------|----------|-------|
| `dogovor_rows.csv` | Договоры с абитуриентами | 7 340 |
| `grafics_rows.csv` | Графики платежей | 9 822 |
| `kvitancii_rows.csv` | Платежи (квитанции) | 6 835 |
| `crit_mag_rows.csv` | Критерии приёма по программам | 148 |
| `plan_rows.csv` | План приёма (бюджет/договор) | 151 |

---

## Слой STG — Схема `stg_mag`

Таблицы хранят сырые данные в TEXT-типах. Столбцы переименованы с кириллицы на латиницу при загрузке.

| Таблица | PK | Строк |
|---------|----|-------|
| `stg_mag.contracts` | `contract_code` | 7 340 |
| `stg_mag.payment_schedules` | `schedule_code` | 9 822 |
| `stg_mag.payments` | `payment_id` (TEXT, формат "00-000001") | 6 835 |
| `stg_mag.criteria` | `(program_name, criteria_id)` | 148 |
| `stg_mag.admission_plan` | `program_name` | 151 |

**Стратегия загрузки:** `INSERT ON CONFLICT DO NOTHING` — повторные запуски безопасны.

---

## Слой ODS — Схема `ods_mag`

Типизированные данные. При каждом запуске — UPSERT: новые добавляются, изменённые обновляются.

| Таблица | PK | Ключевые типы |
|---------|----|---------------|
| `ods_mag.contracts` | `code` | `contract_date DATE`, `discount_percent DECIMAL`, `has_files BOOLEAN` |
| `ods_mag.payment_schedules` | `schedule_code` | `discount_value DECIMAL`, `payment_status TEXT` |
| `ods_mag.payments` | `payment_id` VARCHAR | `payment_date DATE`, `payment_amount DECIMAL` |
| `ods_mag.criteria` | `(program_name, criteria_id)` | `criteria_id INTEGER` |
| `ods_mag.admission_plan` | `program_name` | `budget_seats INTEGER`, `contract_seats INTEGER` |

**Парсеры ODS:**
- Даты: `'23.04.2025 0:00:00'` → `DATE`
- Числа: `'245 000'` / `'10,00'` → `DECIMAL`
- Булевы: `'Да'/'Нет'` → `BOOLEAN`
- Application ID: из текста `"Заявление 00-000002 от 02.04.2025"` → `'00-000002'`
- Applicant code: из текста `"1010125100000 (Молчанов М.А.)"` → `'1010125100000'`

---

## Слой DDS — Схема `dds_mag`

### Измерения (SCD Type 1 — перезапись)

| Таблица | Натуральный ключ | Строк |
|---------|-----------------|-------|
| `dds_mag.dim_applicants` | `applicant_code` UNIQUE | 7 340 |
| `dds_mag.dim_programs` | `program_name` UNIQUE | 184 |
| `dds_mag.dim_criteria` | `(program_name, criteria_id)` UNIQUE | 148 |
| `dds_mag.dim_admission_plans` | `program_name` UNIQUE | 151 |

### Факты (SCD Type 2 — история изменений)

| Таблица | Бизнес-ключ | Отслеживаемые поля | Строк (current) |
|---------|-------------|-------------------|-----------------|
| `dds_mag.fact_contracts` | `ods_contract_code` | `payment_status`, `discount_percent`, `semester_cost` | 7 340 |
| `dds_mag.fact_payment_schedules` | `schedule_code` | `discount_value`, `payment_status` | 2 482 |
| `dds_mag.fact_payments` | `payment_id` | `payment_amount` | 6 835 |

**Логика SCD2:**
1. При первой загрузке — вставить все записи (`valid_from = today`, `valid_to = NULL`, `is_current = TRUE`)
2. При повторной загрузке:
   - Если запись не изменилась → пропустить
   - Если изменилась → закрыть старую (`valid_to = today`, `is_current = FALSE`), вставить новую версию
   - Если запись новая → вставить

**Связи в DDS используют натуральные ключи** (не суррогатные INTEGER FK) — это упрощает загрузку и позволяет избежать многошагового lookup-а после upsert измерений.

---

## Слой MART — Схема `mart_mag`

| Вьюха | Описание | Строк |
|-------|----------|-------|
| `mart_mag.v_mag_contracts` | Текущие договоры с абитуриентом и программой | 7 340 |
| `mart_mag.v_mag_payments` | Платежи с привязкой к договору и программе | 6 835 |
| `mart_mag.v_mag_admission_stats` | Статистика по программам и статусам оплаты | 381 |
| `mart_mag.v_mag_contract_history` | История версий договоров (SCD2, все версии) | — |
| `mart_mag.v_mag_payment_schedule_summary` | Сводка по графикам платежей | — |
| `mart_mag.v_mag_applicant_summary` | Итоги по абитуриентам (договоры, платежи) | — |

---

## Технический стек

| Компонент | Решение |
|-----------|---------|
| БД | Supabase (PostgreSQL 17) |
| Python | 3.x, pandas, sqlalchemy, psycopg2 |
| Загрузка | `COPY → TEMP TABLE → batch INSERT SELECT` (5 000 строк/батч) |
| Идемпотентность | STG: DO NOTHING / ODS+DDS: UPSERT / Факты: SCD2 |
| Логирование | Python logging + tqdm прогресс-бар |

---

## Структура проекта

```
etl_mag_modular/
├── main.py                        # CLI-оркестратор (--layer stg|ods|dds|all --run)
├── config.py                      # Конфиг: CSV-пути, маппинг колонок, подключение к БД
├── extractors.py                  # Чтение CSV + SELECT из ODS/DDS
├── loaders.py                     # COPY+UPSERT+SCD2 (ядро загрузки)
├── transformers/
│   ├── stg_transformer.py         # Добавляет load_date, source_file
│   ├── ods_transformer.py         # Типизация, парсинг дат/ID/decimal
│   └── dds_transformer.py         # Построение измерений и фактов
└── sql/
    ├── 01_stg_mag.sql             # DDL: 5 STG-таблиц
    ├── 02_ods_mag.sql             # DDL: 5 ODS-таблиц
    ├── 03_dds_mag.sql             # DDL: 4 измерения + 3 факт-таблицы
    └── 04_mart_mag.sql            # DDL: 6 аналитических вьюх
```

---

## Запуск

```bash
cd etl_mag_modular

# Dry-run (без записи в БД)
python3 main.py --layer all

# Полный прогон
python3 main.py --layer all --run

# Только один слой
python3 main.py --layer stg --run
python3 main.py --layer ods --run
python3 main.py --layer dds --run
```

---

## Итоговые счётчики (финальный запуск)

```
STG  contracts          7 340
STG  payment_schedules  9 822
STG  payments           6 835
STG  criteria             148
STG  admission_plan       151

ODS  contracts          7 340
ODS  payment_schedules  9 822
ODS  payments           6 835
ODS  criteria             148
ODS  admission_plan       151

DDS  dim_applicants     7 340
DDS  dim_programs         184
DDS  dim_criteria         148
DDS  dim_admission_plans  151
DDS  fact_contracts     7 340  (is_current = TRUE)
DDS  fact_schedules     2 482  (is_current = TRUE)
DDS  fact_payments      6 835  (is_current = TRUE)

MART v_mag_contracts    7 340
MART v_mag_payments     6 835
MART v_mag_adm_stats      381  (программа × статус)
```

---

## Примечания

- `total_sum` и `semester_cost` — отсутствуют в исходном CSV (все NULL); это особенность источника
- `discount_percent` заполнен у 1 184 из 7 340 договоров
- Повторный запуск DDS корректно определяет «нет изменений» и не создаёт дубликатов
- Имена программ в `criteria` и `admission_plan` отличаются от формата в `contracts` — измерения загружаются напрямую из ODS без JOIN с dim_programs
