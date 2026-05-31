# MAG ETL Pipeline (Magistracy Admission Commission)

4-слойный ETL-пайплайн для загрузки данных приемной комиссии магистратуры на Supabase.

## Структура

```
etl_mag_modular/
├── main.py                       # CLI оркестратор
├── config.py                     # Конфигурация БД, пути CSV, маппинги колонок
├── extractors.py                 # Читатели CSV и ODS/DDS выборки
├── loaders.py                    # Батчевая загрузка (100% переиспользование из BAK)
├── validators.py                 # Проверки row counts
├── transformers/
│   ├── stg_transformer.py        # Добавление metadata (load_date, source_file)
│   ├── ods_transformer.py        # Типизация, очистка, парсинг dates/IDs
│   └── dds_transformer.py        # Построение dimensions и facts с SCD2
├── sql/
│   ├── 01_stg_mag.sql            # 5 STG таблиц (raw data)
│   ├── 02_ods_mag.sql            # 5 ODS таблиц (typed, deduplicated)
│   ├── 03_dds_mag.sql            # 4 dimensions + 3 facts + SCD2
│   └── 04_mart_mag.sql           # 6 analytical views
└── requirements.txt              # Зависимости (shared with BAK)
```

## Архитектура: 4 слоя

### STG (Staging)
- Сырые данные из 5 CSV файлов "как есть"
- Все колонки TEXT
- PRIMARY KEY по натуральным ключам
- `ON CONFLICT DO NOTHING` — только дозапись

### ODS (Operational Data Store)
- Типизация: INTEGER, DECIMAL, BOOLEAN, DATE
- Парсинг: русские даты '23.04.2025', декимальные '245 000', boolean 'Да'/'Нет'
- Извлечение: applicant ID из '1010125100000 (ФИО)', application ID из 'Заявление 00-000002...'
- `ON CONFLICT DO UPDATE SET` — перезапись при повторной загрузке
- updated_at TIMESTAMPTZ — время последнего обновления

### DDS (Data Distribution Services)
- Нормализованная 3NF структура
- 4 Dimensions (SCD1): dim_applicants, dim_programs, dim_criteria, dim_admission_plans
- 3 Facts (SCD2): fact_contracts, fact_payment_schedules, fact_payments
- SCD2 история: valid_from, valid_to, is_current BOOLEAN

### MART (Analytics)
- 6 SQL views поверх DDS
- v_mag_contracts, v_mag_payments, v_mag_admission_stats, v_mag_contract_history, 
  v_mag_payment_schedule_summary, v_mag_applicant_summary

## Подготовка

### 1. Установить зависимости
```bash
pip install -r ../etl_bak_modular/requirements.txt
```

### 2. Применить SQL миграции в Supabase

Откройте Supabase SQL Editor и выполните четыре файла в порядке:

```bash
# 1. STG layer
cat sql/01_stg_mag.sql | <paste in Supabase SQL Editor>

# 2. ODS layer
cat sql/02_ods_mag.sql | <paste in Supabase SQL Editor>

# 3. DDS layer
cat sql/03_dds_mag.sql | <paste in Supabase SQL Editor>

# 4. MART layer
cat sql/04_mart_mag.sql | <paste in Supabase SQL Editor>
```

Или используйте MCP apply_migration (если у вас есть project_id):
```bash
# Требуется project_id из https://app.supabase.com/project/<ID>/
apply_migration project_id="xxxx" name="01_stg_mag" query="$(cat sql/01_stg_mag.sql)"
```

### 3. Файл .env.mag

Убедитесь, что .env.mag существует в корне проекта:
```
DB_HOST=aws-0-eu-west-1.pooler.supabase.com
DB_PORT=5432
DB_NAME=postgres
DB_USER=postgres.wvqjeiapjppgkzssewzs
DB_PASSWORD=Angeli030103!
```

## Запуск

### Dry-run (проверка без записи в БД)
```bash
python3 main.py --layer stg
python3 main.py --layer ods
python3 main.py --layer dds
python3 main.py --layer all
```

### Полная загрузка
```bash
# Все слои
python3 main.py --layer all --run

# По слоям
python3 main.py --layer stg --run
python3 main.py --layer ods --run
python3 main.py --layer dds --run
```

### С логированием
```bash
python3 main.py --layer all --run --log-dir ./logs
```

## CSV Источники

| Файл | Строк | Слой | Описание |
|------|-------|------|---------|
| dogovor_rows.csv | 7340 | STG → ODS → DDS | Договоры с подробной информацией |
| grafics_rows.csv | 9822 | STG → ODS → DDS | Графики платежей |
| kvitancii_rows.csv | 6835 | STG → ODS → DDS | Квитанции/платежи |
| crit_mag_rows.csv | 148 | STG → ODS → DDS | Критерии отбора |
| plan_rows.csv | 152 | STG → ODS → DDS | План приема (бюджет/договор места) |

## Проверка

### После STG load
```sql
SELECT COUNT(*) FROM stg_mag.contracts;           -- 7340
SELECT COUNT(*) FROM stg_mag.payment_schedules;   -- 9822
SELECT COUNT(*) FROM stg_mag.payments;            -- 6835
```

### После ODS load
```sql
SELECT COUNT(*) FROM ods_mag.contracts WHERE applicant_code IS NOT NULL;    -- ~7340
SELECT COUNT(*) FROM ods_mag.contracts WHERE contract_date IS NOT NULL;     -- ~7340
SELECT COUNT(DISTINCT applicant_code) FROM ods_mag.contracts;               -- ~7000
```

### После DDS load
```sql
SELECT COUNT(*) FROM dds_mag.dim_applicants;                         -- ~7000
SELECT COUNT(*) FROM dds_mag.dim_programs;                           -- ~25
SELECT COUNT(*) FROM dds_mag.fact_contracts WHERE is_current = TRUE; -- ~7340
SELECT COUNT(*) FROM dds_mag.fact_contracts WHERE is_current = FALSE;-- 0 (first load)
```

### MART views
```sql
SELECT * FROM mart_mag.v_mag_contracts LIMIT 10;
SELECT program_name, COUNT(*) FROM mart_mag.v_mag_contracts GROUP BY program_name;
SELECT * FROM mart_mag.v_mag_admission_stats ORDER BY program_name;
```

## SCD2 История

Отслеживаемые поля для fact tables:
- **fact_contracts**: payment_status, discount_percent, semester_cost
- **fact_payment_schedules**: discount_value, payment_status
- **fact_payments**: payment_amount, payment_status

При изменении любого из этих полей создается новая версия с valid_from/valid_to и is_current флагом.

## Как использовать виды

```sql
-- Текущие контракты с info
SELECT * FROM mart_mag.v_mag_contracts 
WHERE payment_status = 'Не оплачен'
ORDER BY contract_date DESC;

-- История контракта
SELECT * FROM mart_mag.v_mag_contract_history 
WHERE ods_contract_code = 'ПКМ250001'
ORDER BY valid_from;

-- Статистика по программам
SELECT program_name, payment_status, applicant_count 
FROM mart_mag.v_mag_admission_stats
ORDER BY program_name;

-- Итоги по абитуриенту
SELECT * FROM mart_mag.v_mag_applicant_summary 
WHERE code_applicant = '1010125100000';
```

## Troubleshooting

### Timeout при STG load
Если получаете timeout: используется батчевый COPY механизм (5000 rows за раз), что должно работать на Supabase Free. Если все еще падает:
- Уменьшите BATCH_SIZE в config.py (например, до 2000)
- Используйте `--log-dir` для логирования детального хода

### Missing column in rename
Если ошибка о пропущенной колонке в COLUMN_RENAMES: 
- Проверьте точные имена в CSV: `head -1 mag/*.csv`
- Обновите COLUMN_RENAMES в config.py

### FK orphans (DDS)
Если DDS load падает с FK ошибкой:
- ODS данные могут содержать invalid references
- Проверьте logs/etl_mag_*.log для деталей
- Исправьте данные в CSV или добавьте обработку в ODS transformer

## References

- BAK pipeline: `/Users/vadimzenin/ДЗшки/Лика диплом/etl_bak_modular/`
- Plan document: `.claude/plans/` (architecture decisions)
- Supabase docs: https://supabase.com/docs
- PostgreSQL SCD2: https://en.wikipedia.org/wiki/Slowly_changing_dimension
