## Все таблицы в Supabase: полное описание (MAG)

Всего **4 схемы**, **15 таблиц**, **6 вьюх**.

---

## Схема 1: `stg_mag` — Staging (сырые данные)

«Фотография» CSV-файлов. Все поля `TEXT`, никакой типизации. Нужна для того чтобы всегда можно было откатиться к исходнику и понять что именно пришло из файла. При повторной загрузке дубликаты пропускаются (`ON CONFLICT DO NOTHING`).

### `stg_mag.contracts`
| Поле | Тип | Описание |
|---|---|---|
| `contract_code` | TEXT **PK** | Код договора (из «Код») |
| `load_date` | DATE | Дата запуска ETL |
| `source_file` | TEXT | Имя CSV-файла |
| `has_files` | TEXT | Есть прикреплённые файлы (из «Есть файлы») |
| `is_active` | TEXT | Договор активен (из «Активен») |
| `contract_index` | TEXT | Индекс способа заключения (из «Индекс способа заключения договор») |
| `has_errors` | TEXT | Есть ошибки заполнения (из «Есть ошибки заполнения») |
| `applicant_code` | TEXT | Регистрационный номер абитуриента |
| `payment_status` | TEXT | Статус оплаты |
| `applicant_name` | TEXT | ФИО абитуриента (из «Абитуриент») |
| `contract_date` | TEXT | Дата заключения договора |
| `source` | TEXT | Источник (из «Источник») |
| `city` | TEXT | Филиал/город (из «Филиал») |
| `specialization` | TEXT | Конкурсная группа |
| `faculty` | TEXT | Факультет |
| `program_name` | TEXT | Образовательная программа |
| `application_text` | TEXT | Заявление (полный текст, например «Заявление 00-000002 от 02.04.2025») |
| `submission_type` | TEXT | Вид подачи (из «Заявка») |
| `payment_method` | TEXT | Вид оплаты |
| `party_count` | TEXT | Количество сторон договора |
| `customer_type` | TEXT | Тип заказчика |
| `ip_status` | TEXT | Статус ИП |
| `start_date` | TEXT | Дата начала |
| `end_date` | TEXT | Дата окончания |
| `comments` | TEXT | Комментарий |
| `responsible` | TEXT | Ответственный |
| `discount_percent` | TEXT | Процент скидки первого семестра |
| `link` | TEXT | Ссылка |
| `semester_cost` | TEXT | Стоимость первого семестра |
| `total_sum` | TEXT | Сумма договора |
| `customer_name` | TEXT | ФИО заказчика |
| `customer_email` | TEXT | E-mail заказчика (физ. лицо) |
| `email` | TEXT | Email абитуриента |

### `stg_mag.payment_schedules`
| Поле | Тип | Описание |
|---|---|---|
| `schedule_code` | TEXT **PK** | Код графика (из «Код») |
| `load_date` | DATE | Дата загрузки |
| `source_file` | TEXT | Имя файла |
| `owner` | TEXT | Владелец (из «Владелец») |
| `semester_cost` | TEXT | Стоимость семестра |
| `applicant_name` | TEXT | ФИО абитуриента |
| `applicant_code` | TEXT | Код абитуриента |
| `discount_text` | TEXT | Скидка (текст) |
| `discount_value` | TEXT | Значение скидки |
| `payment_status` | TEXT | Статус оплаты |
| `reg_number` | TEXT | Регистрационный номер |
| `discount_percent` | TEXT | Процент скидки |

### `stg_mag.payments`
| Поле | Тип | Описание |
|---|---|---|
| `payment_id` | TEXT **PK** | Номер квитанции — формат «00-000001» (из «Номер») |
| `load_date` | DATE | Дата загрузки |
| `source_file` | TEXT | Имя файла |
| `deletion_mark` | TEXT | Пометка на удаление |
| `payment_date_upload` | TEXT | Дата загрузки платежа |
| `payment_amount` | TEXT | Сумма платежа |
| `contract_code_ref` | TEXT | Ссылка на код договора |
| `payment_name` | TEXT | Наименование платежа |
| `specialization_payment` | TEXT | Специализация (из столбца платежа) |
| `applicant_code` | TEXT | Код абитуриента |
| `has_security_payment` | TEXT | Наличие обеспечительного платежа |
| `applicant_name` | TEXT | ФИО абитуриента |
| `payment_date` | TEXT | Дата платежа |
| `payment_comments` | TEXT | Комментарии к платежу |
| `payment_type` | TEXT | Вид платежа |
| `payment_responsible` | TEXT | Ответственный |

### `stg_mag.criteria`
| Поле | Тип | Описание |
|---|---|---|
| `program_name` | TEXT **PK (часть)** | Название программы |
| `criteria_id` | TEXT **PK (часть)** | Идентификатор критерия |
| `load_date` | DATE | Дата загрузки |
| `source_file` | TEXT | Имя файла |

### `stg_mag.admission_plan`
| Поле | Тип | Описание |
|---|---|---|
| `program_name` | TEXT **PK** | Название программы |
| `budget_seats` | TEXT | Бюджетные места |
| `contract_seats` | TEXT | Места по договорам |
| `load_date` | DATE | Дата загрузки |
| `source_file` | TEXT | Имя файла |

---

## Схема 2: `ods_mag` — Operational Data Store (текущее состояние)

Та же информация что в STG, но с типизацией и с гарантией «одна строка = один объект». При повторной загрузке строки **обновляются**, а не дублируются. Поле `updated_at` фиксирует время последнего обновления.

### `ods_mag.contracts`
| Поле | Тип | Описание |
|---|---|---|
| `code` | VARCHAR **PK** | Код договора (внутренний уникальный код — ODS-ключ) |
| `updated_at` | TIMESTAMPTZ | Время последнего обновления |
| `has_files` | BOOLEAN | Есть прикреплённые файлы |
| `is_active` | INTEGER | Статус активности договора |
| `contract_code` | TEXT | Номер договора (читаемый, например «ПКМ250001») |
| `applicant_code` | VARCHAR | Регистрационный номер абитуриента |
| `payment_status` | TEXT | Статус оплаты |
| `applicant_name` | TEXT | ФИО абитуриента |
| `contract_date` | DATE | Дата заключения договора |
| `source` | TEXT | Источник данных |
| `city` | TEXT | Филиал/город |
| `specialization` | TEXT | Конкурсная группа |
| `faculty` | TEXT | Факультет |
| `program_name` | TEXT | Образовательная программа |
| `application_id` | VARCHAR | Извлечённый ID заявления («00-000002» из текста «Заявление 00-000002…») |
| `application_text` | TEXT | Полный текст поля заявления |
| `contract_index` | TEXT | Индекс способа заключения |
| `has_errors` | BOOLEAN | Есть ошибки заполнения |
| `submission_type` | TEXT | Вид подачи |
| `payment_method` | TEXT | Вид оплаты |
| `party_count` | INTEGER | Количество сторон договора |
| `customer_type` | TEXT | Тип заказчика |
| `ip_status` | TEXT | Статус ИП |
| `start_date` | DATE | Дата начала договора |
| `end_date` | DATE | Дата окончания договора |
| `comments` | TEXT | Комментарий |
| `responsible` | TEXT | Ответственный менеджер |
| `discount_percent` | NUMERIC | Процент скидки (например 10.00) |
| `link` | TEXT | Ссылка |
| `semester_cost` | NUMERIC | Стоимость первого семестра |
| `total_sum` | NUMERIC | Сумма договора |
| `customer_name` | TEXT | ФИО заказчика |
| `customer_email` | TEXT | Email заказчика |
| `email` | TEXT | Email абитуриента |

### `ods_mag.payment_schedules`
| Поле | Тип | Описание |
|---|---|---|
| `schedule_code` | VARCHAR **PK** | Код графика платежей |
| `updated_at` | TIMESTAMPTZ | Время обновления |
| `owner` | TEXT | Владелец графика |
| `semester_cost` | NUMERIC | Стоимость семестра |
| `applicant_name` | TEXT | ФИО абитуриента |
| `applicant_code` | VARCHAR | Код абитуриента |
| `discount_text` | TEXT | Скидка в текстовом виде |
| `discount_value` | NUMERIC | Числовое значение скидки |
| `payment_status` | TEXT | Статус оплаты |
| `reg_number` | VARCHAR | Регистрационный номер |
| `discount_percent` | NUMERIC | Процент скидки |

### `ods_mag.payments`
| Поле | Тип | Описание |
|---|---|---|
| `payment_id` | VARCHAR **PK** | Номер квитанции — строка формата «00-000001» |
| `updated_at` | TIMESTAMPTZ | Время обновления |
| `deletion_mark` | BOOLEAN | Пометка на удаление |
| `payment_date_upload` | DATE | Дата загрузки платежа |
| `payment_amount` | NUMERIC | Сумма платежа |
| `contract_code` | VARCHAR | Код связанного договора |
| `payment_name` | TEXT | Наименование платежа |
| `specialization` | TEXT | Специализация |
| `applicant_code` | VARCHAR | Код абитуриента |
| `has_security_payment` | BOOLEAN | Наличие обеспечительного платежа |
| `applicant_name` | TEXT | ФИО абитуриента |
| `payment_date` | DATE | Дата платежа |
| `comments` | TEXT | Комментарии |
| `payment_type` | TEXT | Вид платежа |
| `responsible` | TEXT | Ответственный |

### `ods_mag.criteria`
| Поле | Тип | Описание |
|---|---|---|
| `program_name` | TEXT **PK (часть)** | Название программы |
| `criteria_id` | INTEGER **PK (часть)** | Числовой идентификатор критерия |
| `updated_at` | TIMESTAMPTZ | Время обновления |

### `ods_mag.admission_plan`
| Поле | Тип | Описание |
|---|---|---|
| `program_name` | VARCHAR **PK** | Название программы |
| `budget_seats` | INTEGER | Количество бюджетных мест |
| `contract_seats` | INTEGER | Количество мест по договорам |
| `updated_at` | TIMESTAMPTZ | Время обновления |

---

## Схема 3: `dds_mag` — Detailed Data Store (нормализация + история)

Данные приведены к **3NF**: справочники вынесены отдельно, факты ссылаются на них через натуральные ключи. История изменений хранится через **SCD Type 2** в факт-таблицах.

---

### `dds_mag.dim_applicants` — справочник абитуриентов

**Одна строка = один уникальный абитуриент.** Строится из `ods_mag.contracts`.

| Поле | Тип | Описание |
|---|---|---|
| `applicant_id` | BIGSERIAL **PK** | Суррогатный ключ, генерируется автоматически |
| `applicant_code` | VARCHAR UNIQUE NOT NULL | Натуральный ключ — регистрационный номер абитуриента |
| `full_name` | TEXT | ФИО абитуриента |
| `email` | TEXT | Email абитуриента |
| `updated_at` | TIMESTAMPTZ | Время последнего обновления |

**Зачем нужна:** чтобы не хранить ФИО и email в каждой строке договора и платежа. 7 340 уникальных абитуриентов.

---

### `dds_mag.dim_programs` — справочник программ

**Одна строка = одна уникальная образовательная программа.**

| Поле | Тип | Описание |
|---|---|---|
| `program_id` | BIGSERIAL **PK** | Суррогатный ключ |
| `program_name` | TEXT UNIQUE NOT NULL | Полное название программы |
| `specialization` | TEXT | Конкурсная группа/специализация |
| `faculty` | TEXT | Факультет |
| `updated_at` | TIMESTAMPTZ | Время обновления |

**Зачем нужна:** 184 уникальных программы; название программы присутствует в тысячах договоров — без справочника оно повторялось бы в каждой строке.

---

### `dds_mag.dim_criteria` — справочник критериев приёма

**Одна строка = один критерий приёма для конкретной программы.**

| Поле | Тип | Описание |
|---|---|---|
| `dim_criteria_id` | BIGSERIAL **PK** | Суррогатный ключ |
| `program_name` | TEXT NOT NULL | Название программы (натуральный FK → dim_programs) |
| `criteria_id` | INTEGER | Числовой идентификатор критерия из источника |
| `updated_at` | TIMESTAMPTZ | Время обновления |

> **Примечание:** имена программ в `crit_mag_rows.csv` отличаются по формату от `dogovor_rows.csv`, поэтому измерение загружается напрямую из ODS без JOIN с dim_programs. 148 строк.

---

### `dds_mag.dim_admission_plans` — план приёма

**Одна строка = план приёма (бюджет/договор) для одной программы.**

| Поле | Тип | Описание |
|---|---|---|
| `plan_id` | BIGSERIAL **PK** | Суррогатный ключ |
| `program_name` | TEXT UNIQUE NOT NULL | Название программы |
| `budget_seats` | INTEGER | Количество бюджетных мест |
| `contract_seats` | INTEGER | Количество мест по договорам |
| `updated_at` | TIMESTAMPTZ | Время обновления |

> **Примечание:** формат названий программ в `plan_rows.csv` отличается от контрактов, поэтому JOIN с dim_programs не применяется. 151 строка.

---

### `dds_mag.fact_contracts` — факт договоров (SCD Type 2)

**Одна строка = одна версия договора.** При изменении `payment_status`, `discount_percent` или `semester_cost` старая строка закрывается, вставляется новая версия.

| Поле | Тип | Описание |
|---|---|---|
| `contract_id` | BIGSERIAL **PK** | Суррогатный ключ версии |
| `ods_contract_code` | VARCHAR NOT NULL | Натуральный ключ — код договора из ODS |
| `applicant_code` | VARCHAR | Код абитуриента (натуральный FK → dim_applicants) |
| `program_name` | TEXT | Название программы (натуральный FK → dim_programs) |
| `application_id` | VARCHAR | ID заявления |
| `has_files` | BOOLEAN | Есть прикреплённые файлы |
| `is_active` | INTEGER | Статус активности |
| `payment_status` | TEXT | Статус оплаты — **отслеживается SCD2** |
| `discount_percent` | NUMERIC | Процент скидки — **отслеживается SCD2** |
| `semester_cost` | NUMERIC | Стоимость семестра — **отслеживается SCD2** |
| `total_sum` | NUMERIC | Сумма договора |
| `valid_from` | DATE NOT NULL | Дата начала актуальности версии |
| `valid_to` | DATE | Дата окончания (NULL = актуальна сейчас) |
| `is_current` | BOOLEAN | TRUE = текущая версия |
| `load_date` | DATE | Дата загрузки ETL |

**Как работает история:** если статус оплаты изменился с «Не оплачен» на «Оплачен по квитанциям», в таблице будет две строки:

```
ods_contract_code | payment_status       | valid_from | valid_to   | is_current
------------------|-----------------------|------------|------------|----------
ПКМ250001         | Не оплачен            | 2026-05-16 | 2026-06-01 | FALSE
ПКМ250001         | Оплачен по квитанциям | 2026-06-01 | NULL       | TRUE
```

---

### `dds_mag.fact_payment_schedules` — факт графиков платежей (SCD Type 2)

**Одна строка = одна версия графика.** Отслеживаются `discount_value` и `payment_status`.

| Поле | Тип | Описание |
|---|---|---|
| `fact_schedule_id` | BIGSERIAL **PK** | Суррогатный ключ версии |
| `schedule_code` | VARCHAR NOT NULL | Натуральный ключ — код графика из ODS |
| `applicant_code` | VARCHAR | Код абитуриента (натуральный FK → dim_applicants) |
| `owner` | TEXT | Владелец графика |
| `discount_value` | NUMERIC | Числовое значение скидки — **отслеживается SCD2** |
| `payment_status` | TEXT | Статус оплаты — **отслеживается SCD2** |
| `valid_from` | DATE NOT NULL | Дата начала актуальности |
| `valid_to` | DATE | Дата окончания (NULL = актуальна) |
| `is_current` | BOOLEAN | TRUE = текущая версия |
| `load_date` | DATE | Дата загрузки ETL |

---

### `dds_mag.fact_payments` — факт платежей (SCD Type 2)

**Одна строка = одна версия платежа.** Отслеживается `payment_amount`.

| Поле | Тип | Описание |
|---|---|---|
| `fact_payment_id` | BIGSERIAL **PK** | Суррогатный ключ версии |
| `payment_id` | VARCHAR NOT NULL | Натуральный ключ — номер квитанции формата «00-000001» |
| `applicant_code` | VARCHAR | Код абитуриента (натуральный FK → dim_applicants) |
| `contract_code` | VARCHAR | Код связанного договора |
| `payment_date` | DATE | Дата платежа |
| `payment_amount` | NUMERIC | Сумма платежа — **отслеживается SCD2** |
| `payment_name` | TEXT | Наименование платежа |
| `has_security_payment` | BOOLEAN | Наличие обеспечительного платежа |
| `valid_from` | DATE NOT NULL | Дата начала актуальности |
| `valid_to` | DATE | Дата окончания (NULL = актуальна) |
| `is_current` | BOOLEAN | TRUE = текущая версия |
| `load_date` | DATE | Дата загрузки ETL |

---

## Схема 4: `mart_mag` — витрины (только вьюхи, без таблиц)

SQL-представления поверх DDS — только для чтения. Аналитик пишет запрос к витрине и получает готовый результат без ручных JOIN-ов.

| Вьюха | Что показывает |
|---|---|
| `v_mag_contracts` | Текущие договоры с ФИО абитуриента, программой, статусом оплаты, скидкой |
| `v_mag_payments` | Текущие платежи с привязкой к договору, программе и абитуриенту |
| `v_mag_admission_stats` | Статистика по программам: количество договоров, абитуриентов, выручка, скидки, план мест |
| `v_mag_contract_history` | **Полная история** изменений договоров — все SCD2-версии с номером версии |
| `v_mag_payment_schedule_summary` | Сводка по графикам: сколько платежей, итоговая сумма, последняя дата платежа |
| `v_mag_applicant_summary` | Итоги по абитуриенту: кол-во договоров, платежей, программы, суммы |

---

## Итоговые счётчики

| Слой | Таблица | Строк |
|------|---------|-------|
| STG | contracts | 7 340 |
| STG | payment_schedules | 9 822 |
| STG | payments | 6 835 |
| STG | criteria | 148 |
| STG | admission_plan | 151 |
| ODS | contracts | 7 340 |
| ODS | payment_schedules | 9 822 |
| ODS | payments | 6 835 |
| ODS | criteria | 148 |
| ODS | admission_plan | 151 |
| DDS | dim_applicants | 7 340 |
| DDS | dim_programs | 184 |
| DDS | dim_criteria | 148 |
| DDS | dim_admission_plans | 151 |
| DDS | fact_contracts (is_current) | 7 340 |
| DDS | fact_payment_schedules (is_current) | 2 482 |
| DDS | fact_payments (is_current) | 6 835 |
