
import logging
from sqlalchemy import text

log = logging.getLogger('etl_bak')

MAX_PRIORITIES = 20

def _build_enriched_sql() -> str:
    cases = []
    pivot_cols = []
    for i in range(1, MAX_PRIORITIES + 1):
        cases.append(f"""
            MAX(CASE WHEN prio = {i} THEN city       END) AS city_p{i},
            MAX(CASE WHEN prio = {i} THEN specialization END) AS spec_p{i},
            MAX(CASE WHEN prio = {i} THEN program    END) AS prog_p{i},
            MAX(CASE WHEN prio = {i} THEN sum_points END) AS score_p{i},
            MAX(CASE WHEN prio = {i} THEN payment_status END) AS pay_status_p{i}""")
        pivot_cols.append(
            f"pa.city_p{i}, pa.spec_p{i}, pa.prog_p{i}, pa.score_p{i}, pa.pay_status_p{i}"
        )

    cases_sql      = ',\n'.join(cases)
    pivot_cols_sql = ',\n        '.join(pivot_cols)

    return f"""
    DROP TABLE IF EXISTS mart_bak.enriched_students_data;

    CREATE TABLE mart_bak.enriched_students_data AS
    WITH AppDetails AS (
        -- Все заявления из DDS: абитуриент + программа + баллы + статус оплаты
        SELECT
            da.uniq_code::float::bigint   AS u_code,
            fa.priority::int              AS prio,
            dp.city,
            dp.specialization,
            dp.program,
            fc.payment_status,
            fs.rank2                      AS sum_points
        FROM dds_bak.fact_applications fa
        JOIN  dds_bak.dim_applicants da ON da.applicant_id = fa.applicant_id
        JOIN  dds_bak.dim_programs   dp ON dp.program_id   = fa.program_id
        LEFT JOIN dds_bak.fact_contracts fc
            ON  fc.applicant_id = fa.applicant_id
            AND fc.program_id   = fa.program_id
            AND fc.priority     = fa.priority
            AND fc.is_current   = TRUE
        LEFT JOIN dds_bak.fact_scores fs
            ON  fs.applicant_id = fa.applicant_id
            AND fs.program_id   = fa.program_id
            AND fs.priority     = fa.priority
            AND fs.is_current   = TRUE
        WHERE fa.is_current     = TRUE
          AND fa.priority::int <= {MAX_PRIORITIES}
          AND da.uniq_code IS NOT NULL
    ),
    PivotedApps AS (
        -- Разворачиваем приоритеты в столбцы
        SELECT
            u_code,
            {cases_sql}
        FROM AppDetails
        GROUP BY u_code
    )
    -- Базовая строка: один договор = одна строка + 100 колонок приоритетов
    SELECT
        fc_main.dogovor,
        fc_main.contract_date,
        da_main.full_name,
        da_main.code_applicant,
        da_main.uniq_code,
        dp_main.city,
        dp_main.program,
        dp_main.specialization,
        fc_main.priority,
        CASE
            WHEN fa_main.app_id ~ '^00-'
                THEN fa_main.app_id
            WHEN fa_main.app_id ~ '^[0-9]+$'
                THEN '00-' || LPAD(fa_main.app_id::bigint::text, 9, '0')
            ELSE fa_main.app_id
        END                           AS id_application,
        fc_main.admission_plan,
        fc_main.payment_status,
        fc_main.name_parent,
        fc_main.number_parent,
        fc_main.bvi,
        fc_main.ege,
        fc_main.individual_achievements,
        fc_main.total,
        {pivot_cols_sql}
    FROM dds_bak.fact_contracts fc_main
    JOIN  dds_bak.dim_applicants da_main ON da_main.applicant_id = fc_main.applicant_id
    JOIN  dds_bak.dim_programs   dp_main ON dp_main.program_id   = fc_main.program_id
    LEFT JOIN dds_bak.fact_applications fa_main
          ON  fa_main.applicant_id = fc_main.applicant_id
          AND fa_main.program_id   = fc_main.program_id
          AND fa_main.priority     = fc_main.priority
          AND fa_main.is_current   = TRUE
    LEFT JOIN PivotedApps pa
        ON da_main.uniq_code::float::bigint = pa.u_code
    WHERE fc_main.is_current = TRUE;
    """

def run_mart(engine, dry_run: bool):
    log.info("Началась стадия MART")

    if dry_run:
        log.info("Стадия MART успешно завершилась")
        return

    sql = _build_enriched_sql()
    with engine.begin() as conn:
        conn.execute(text(sql))

    with engine.connect() as conn:
        count = conn.execute(
            text('SELECT COUNT(*) FROM mart_bak.enriched_students_data')
        ).scalar()
    log.info("mart enriched_students_data: %d строк", count)
    log.info("Стадия MART успешно завершилась")
