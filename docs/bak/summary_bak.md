## Саммари: ETL-пайплайн бакалавриата (БАК) — что было сделано

---

### Что за система

Полноценный 4-слойный ETL-пайплайн для загрузки данных приёмной комиссии бакалавриата из CSV-файлов в PostgreSQL (Supabase). Данные проходят через 4 слоя: сырые → очищенные → нормализованные → аналитические.

---

### Источники данных (4 CSV-файла)

| Файл | Строк | Описание |
|---|---|---|
| `application_bak_rows.csv` | 44 648 | Заявления абитуриентов |
| `ball_bak_rows.csv` | 57 030 | Баллы и рейтинги |
| `dogovor_bak_rows.csv` | 7 066 | Договоры о зачислении |
| `kriterii_bak_rows.csv` | 72 | Критерии отбора по программам |

---

### Архитектура: 4 слоя

#### Слой 1 — STG (`stg_bak`)
**Назначение:** сырое хранилище CSV "как есть".  
**Принципы:**
- Все колонки `TEXT`, никаких типов
- Натуральные ключи из CSV как `PRIMARY KEY` (`id`, `nomer`, `dogovor`, `scep`)
- `ON CONFLICT DO NOTHING` — только дозапись, никогда не обновляет
- Дополнительные поля: `load_date DATE`, `source_file TEXT`
- Кириллические имена колонок переименованы в латиницу (маппинг в `config.py`)
- Пустой столбец `Ранг` (0% данных) — дропается при загрузке

#### Слой 2 — ODS (`ods_bak`)
**Назначение:** актуальное состояние с типизацией, одна строка на объект.  
**Принципы:**
- Натуральный ключ как `PRIMARY KEY` (`app_id`, `nomer`, `dogovor`, `scep`)
- Типизация: `INTEGER`, `DECIMAL`, `BOOLEAN`, `DATE` — всё остальное `TEXT`
- Все поля кроме PK — `NULLABLE` (данные не всегда полные)
- `ON CONFLICT DO UPDATE SET` — перезаписывает при повторной загрузке
- Колонка `updated_at TIMESTAMPTZ DEFAULT NOW()` обновляется при каждом upsert
- Парсинг: `"Да"/"Нет"` → `TRUE/FALSE`, `"245 000"` → `245000.0`, `"3,14"` → `3.14`

#### Слой 3 — DDS (`dds_bak`)
**Назначение:** нормализованная 3NF-структура с историей изменений (SCD Type 2).

**Справочники (SCD Type 1 — перезапись):**
- `dim_applicants` — уникальные абитуриенты, ключ: `code_applicant` (собирается из всех 3 ODS-таблиц)
- `dim_programs` — уникальные программы, составной ключ: `(program, specialization, city)`
- `dim_criteria` — критерии отбора, ключ: `scep`; `program_id` резолюцится через `groupby(program_name).first()`

**Фактовые таблицы (SCD Type 2 — история):**
- `fact_applications` — отслеживаемые поля: `sspvo_status`, `priority`
- `fact_scores` — отслеживаемые поля: `rank2`, `rank3`, `rank4`, `rank5`, `rank6`
- `fact_contracts` — отслеживаемые поля: `payment_status`, `total`

Каждая фактовая таблица имеет: суррогатный `BIGSERIAL PK`, `applicant_id FK`, `program_id FK`, `valid_from`, `valid_to`, `is_current BOOLEAN`.

**Логика SCD2:** `classify_scd2_changes()` векторно сравнивает новые данные с текущими (`is_current=TRUE`). Изменившиеся строки → старая закрывается (`valid_to=today, is_current=FALSE`), новая вставляется. UPDATE и INSERT в **одной транзакции** — нет окна потери данных.

#### Слой 4 — MART (`mart_bak`)
**Назначение:** SQL-вьюхи для аналитики поверх DDS, без Python.  
Вьюхи: `v_applications`, `v_contracts`, `v_scores`, `v_payment_summary`, `v_admission_stats`, `v_contract_history`.

---

### Файловая структура Python ETL

```
etl_bak_modular/
├── main.py              # CLI-оркестратор, 4 функции run_stg/run_ods/run_dds + логирование
├── config.py            # подключение к БД, пути CSV, маппинги колонок, setup_logging()
├── extractors.py        # чтение CSV и выборки из БД
├── loaders.py           # вся логика записи в БД
├── validators.py        # проверки после загрузки каждого слоя
└── transformers/
    ├── stg_transformer.py   # добавляет load_date, source_file
    ├── ods_transformer.py   # типизация, очистка, парсинг
    └── dds_transformer.py   # сборка справочников и фактов, SCD2-логика
```

---

### Механизм загрузки в БД (ключевое решение)

**Проблема:** Supabase Free plan обрывает INSERT-запросы по таймауту (~2 мин) при загрузке 44к+ строк.

**Решение: COPY → temp → батчевый INSERT SELECT:**
1. `COPY` весь DataFrame в temp-таблицу (без индексов — мгновенно, не подпадает под таймаут)
2. `ALTER TABLE tmp ADD COLUMN _etl_rn SERIAL` — суррогатный rownum для стабильного порядка
3. Батчи по 5000 строк: `INSERT INTO real SELECT FROM tmp ORDER BY _etl_rn LIMIT 5000 OFFSET 0` — каждый запрос выполняется за секунды
4. `SET lock_timeout = '15s'` — быстрый отказ вместо вечного зависания при блокировке
5. `except BaseException` — Ctrl+C тоже делает rollback, не оставляет висячих блокировок

**Temp-таблицы именуются с префиксом слоя** (`_tmp_stg_applications`, `_tmp_ods_applications`) — нет коллизий между слоями.

**Сериализация в TSV:** кастомная функция `_df_to_tsv()` — обрабатывает `None`, `float NaN`, `pd.NA` (nullable Int64), целые float (`1.0` → `"1"`), экранирует `\t \n \r \\`.

---

### Запуск

```bash
# Установить зависимости
pip install -r requirements.txt

# Полный пайплайн
python3 main.py --layer all --run

# По слоям
python3 main.py --layer stg --run
python3 main.py --layer ods --run
python3 main.py --layer dds --run

# С файлом лога
python3 main.py --layer all --run --log-dir ./logs

# Dry-run (без записи в БД)
python3 main.py --layer all
```

`.env` файл:
```
DB_HOST=...
DB_PORT=6543
DB_NAME=postgres
DB_USER=postgres
DB_PASSWORD=...
```

---

### Для репликации на магистратуру — чек-лист

1. **Проанализировать CSV** — колонки, типы, покрытие, натуральные ключи, пустые поля
2. **Написать маппинг колонок** в `config.py` (кириллица → латиница, опечатки)
3. **Создать SQL-схемы** — `stg_mag`, `ods_mag`, `dds_mag`, `mart_mag` по той же структуре
4. **Задеплоить SQL** в Supabase через MCP (`apply_migration`)
5. **Написать трансформеры** — stg (только мета), ods (типизация), dds (справочники + факты)
6. **Определить SCD2-поля** — какие поля отслеживать как "изменение" в фактах
7. **Настроить валидаторы** с реальными порогами строк
8. **Запустить** `--layer all --run`