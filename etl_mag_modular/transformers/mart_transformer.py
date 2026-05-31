
import io
import re
import logging
import pandas as pd
from datetime import date, datetime
from sqlalchemy import text

log = logging.getLogger('etl_mag')

_REPORT_SQL = r"""
DROP TABLE IF EXISTS mart_mag."__OUT__";
CREATE TABLE mart_mag."__OUT__" AS
WITH
CleanPlan AS (
    SELECT
        contract_seats::numeric AS plan_val,
        LOWER(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(
            program_name, '\s*/.*$', ''), '\s*\(.*?\)', '', 'g'),
            '^[0-9\.]+\s*', ''), '\s+', ' ', 'g'))) AS clean_prog
    FROM ods_mag.admission_plan
),
CleanCrit AS (
    SELECT
        criteria_id AS crit_val,
        LOWER(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(
            program_name, '\s*/.*$', ''), '\s*\(.*?\)', '', 'g'),
            '^[0-9\.]+\s*', ''), '\s+', ' ', 'g'))) AS clean_prog
    FROM ods_mag.criteria
),
BaseStats AS (
    SELECT
        "1"::integer AS row_num,
        "2" AS prog_name,
        LOWER(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(
            "2", '\s*/.*$', ''), '\s*\(.*?\)', '', 'g'),
            '^[0-9\.]+\s*', ''), '\s+', ' ', 'g'))) AS clean_prog,
        CAST(NULLIF(REPLACE("5"::text, ' ', ''), '') AS numeric) AS archive_col5,
        CASE
            WHEN "2" ILIKE '%ИТОГО%'                               THEN 0
            WHEN "2" IN ('Очное обучение','Очно-заочное обучение') THEN 1
            WHEN "2" LIKE 'Направление подготовки%'                THEN 2
            ELSE 3
        END AS level
    FROM "__TPL__"
    WHERE "1" IS NOT NULL AND TRIM("1"::text) ~ '^[0-9]+$'
),
Hierarchy AS (
    SELECT *,
        SUM(CASE WHEN level IN (0,1)   THEN 1 ELSE 0 END) OVER (ORDER BY row_num) AS grp_form,
        SUM(CASE WHEN level IN (0,1,2) THEN 1 ELSE 0 END) OVER (ORDER BY row_num) AS grp_dir
    FROM BaseStats
),
ContractMetrics AS (
    SELECT
        LOWER(TRIM(REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(
            c.specialization, '\s*/.*$', ''), '\s*\(.*?\)', '', 'g'),
            '^[0-9\.]+\s*', ''), '\s+', ' ', 'g'))) AS clean_prog,
        COUNT(CASE WHEN c.is_active = 2                                THEN 1 END) AS val_5,
        COUNT(CASE WHEN c.payment_status != 'Не оплачен'              THEN 1 END) AS val_8,
        SUM(CASE WHEN c.is_active = 2 THEN (
            SELECT COALESCE(SUM(p.payment_amount), 0)
            FROM ods_mag.payments p WHERE p.applicant_code = c.applicant_code
        ) ELSE 0 END)                                                              AS val_9,
        COUNT(CASE WHEN c.is_active = 2
                    AND c.payment_method ILIKE '%Кредит%'              THEN 1 END) AS val_11,
        COUNT(CASE WHEN c.is_active = 2
                    AND c.payment_method ILIKE '%Материнский капитал%' THEN 1 END) AS val_12,
        COUNT(CASE WHEN c.is_active = 2 AND EXISTS(
            SELECT 1 FROM ods_mag.payment_schedules ps
            WHERE ps.reg_number = c.applicant_code
              AND COALESCE(ps.discount_percent, 0) > 0
        )                                                              THEN 1 END) AS val_14
    FROM ods_mag.contracts c
    GROUP BY clean_prog
),
RawLevel3 AS (
    SELECT
        h.*,
        (SELECT MAX(p.plan_val) FROM CleanPlan p WHERE p.clean_prog = h.clean_prog) AS v3,
        (SELECT MAX(c.crit_val) FROM CleanCrit c WHERE c.clean_prog = h.clean_prog) AS v4,
        COALESCE(cm.val_5,  0) AS v5,
        COALESCE(cm.val_8,  0) AS v8,
        COALESCE(cm.val_9,  0) AS v9,
        COALESCE(cm.val_11, 0) AS v11,
        COALESCE(cm.val_12, 0) AS v12,
        COALESCE(cm.val_14, 0) AS v14
    FROM Hierarchy h
    LEFT JOIN ContractMetrics cm ON cm.clean_prog = h.clean_prog
    WHERE h.level = 3
),
FinalCalc AS (
    SELECT
        h.row_num, h.prog_name, h.archive_col5,
        CASE WHEN h.level=3 THEN (SELECT v3  FROM RawLevel3 r WHERE r.row_num=h.row_num)
             WHEN h.level=2 THEN (SELECT SUM(v3)  FROM RawLevel3 r WHERE r.grp_dir =h.grp_dir)
             WHEN h.level=1 THEN (SELECT SUM(v3)  FROM RawLevel3 r WHERE r.grp_form=h.grp_form)
             WHEN h.level=0 THEN (SELECT SUM(v3)  FROM RawLevel3 r) END AS f3,
        CASE WHEN h.level=3 THEN (SELECT v4  FROM RawLevel3 r WHERE r.row_num=h.row_num)
             ELSE NULL END AS f4,
        CASE WHEN h.level=3 THEN (SELECT v5  FROM RawLevel3 r WHERE r.row_num=h.row_num)
             WHEN h.level=2 THEN (SELECT SUM(v5)  FROM RawLevel3 r WHERE r.grp_dir =h.grp_dir)
             WHEN h.level=1 THEN (SELECT SUM(v5)  FROM RawLevel3 r WHERE r.grp_form=h.grp_form)
             WHEN h.level=0 THEN (SELECT SUM(v5)  FROM RawLevel3 r) END AS f5,
        CASE WHEN h.level=3 THEN (SELECT v8  FROM RawLevel3 r WHERE r.row_num=h.row_num)
             WHEN h.level=2 THEN (SELECT SUM(v8)  FROM RawLevel3 r WHERE r.grp_dir =h.grp_dir)
             WHEN h.level=1 THEN (SELECT SUM(v8)  FROM RawLevel3 r WHERE r.grp_form=h.grp_form)
             WHEN h.level=0 THEN (SELECT SUM(v8)  FROM RawLevel3 r) END AS f8,
        CASE WHEN h.level=3 THEN (SELECT v9  FROM RawLevel3 r WHERE r.row_num=h.row_num)
             WHEN h.level=2 THEN (SELECT SUM(v9)  FROM RawLevel3 r WHERE r.grp_dir =h.grp_dir)
             WHEN h.level=1 THEN (SELECT SUM(v9)  FROM RawLevel3 r WHERE r.grp_form=h.grp_form)
             WHEN h.level=0 THEN (SELECT SUM(v9)  FROM RawLevel3 r) END AS f9,
        CASE WHEN h.level=3 THEN (SELECT v11 FROM RawLevel3 r WHERE r.row_num=h.row_num)
             WHEN h.level=2 THEN (SELECT SUM(v11) FROM RawLevel3 r WHERE r.grp_dir =h.grp_dir)
             WHEN h.level=1 THEN (SELECT SUM(v11) FROM RawLevel3 r WHERE r.grp_form=h.grp_form)
             WHEN h.level=0 THEN (SELECT SUM(v11) FROM RawLevel3 r) END AS f11,
        CASE WHEN h.level=3 THEN (SELECT v12 FROM RawLevel3 r WHERE r.row_num=h.row_num)
             WHEN h.level=2 THEN (SELECT SUM(v12) FROM RawLevel3 r WHERE r.grp_dir =h.grp_dir)
             WHEN h.level=1 THEN (SELECT SUM(v12) FROM RawLevel3 r WHERE r.grp_form=h.grp_form)
             WHEN h.level=0 THEN (SELECT SUM(v12) FROM RawLevel3 r) END AS f12,
        CASE WHEN h.level=3 THEN (SELECT v14 FROM RawLevel3 r WHERE r.row_num=h.row_num)
             WHEN h.level=2 THEN (SELECT SUM(v14) FROM RawLevel3 r WHERE r.grp_dir =h.grp_dir)
             WHEN h.level=1 THEN (SELECT SUM(v14) FROM RawLevel3 r WHERE r.grp_form=h.grp_form)
             WHEN h.level=0 THEN (SELECT SUM(v14) FROM RawLevel3 r) END AS f14
    FROM Hierarchy h
)
SELECT
    ROW_NUMBER() OVER (ORDER BY row_num::integer)::integer AS "1",
    prog_name                                              AS "2",
    COALESCE(f3,  0)::text                                 AS "3",
    f4::text                                               AS "4",
    COALESCE(f5,  0)::text                                 AS "5",
    COALESCE(archive_col5, 0)::text                        AS "6",
    (COALESCE(f5,0) - COALESCE(archive_col5,0))::text      AS "7",
    COALESCE(f8,  0)::text                                 AS "8",
    COALESCE(f9,  0)::text                                 AS "9",
    COALESCE(f11, 0)::text                                 AS "11",
    COALESCE(f12, 0)::text                                 AS "12",
    COALESCE(f14, 0)::text                                 AS "14"
FROM FinalCalc
WHERE prog_name IS NOT NULL AND TRIM(prog_name) != ''
ORDER BY row_num::integer;
"""

def _get_yesterday_counts(engine, today_str: str) -> dict:
    with engine.connect() as conn:
        row = conn.execute(text("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'mart_mag'
              AND table_name LIKE 'stats_%'
              AND table_name <> :today
            ORDER BY table_name DESC LIMIT 1
        """), {"today": f"stats_{today_str}"}).fetchone()

        if not row:
            log.info("Предыдущих таблиц stats_* не найдено — вчерашние данные = 0")
            return {}

        prev = row[0]
        log.info("Вчерашние данные: таблица 'mart_mag.%s'", prev)
        df = pd.read_sql(f'SELECT "2", "5" FROM mart_mag."{prev}"', conn)
        return dict(zip(
            df["2"],
            pd.to_numeric(df["5"], errors="coerce").fillna(0).astype(int)
        ))

def build_stats_template(engine, today_str: str) -> pd.DataFrame:
    with engine.connect() as conn:
        tpl = pd.read_sql(
            'SELECT "1"::text AS "1", "2" FROM mart_mag.stats ORDER BY "1"::integer',
            conn
        )

    yesterday = _get_yesterday_counts(engine, today_str)
    tpl["5"] = tpl["2"].map(lambda name: str(yesterday.get(name, 0)))

    df = tpl[["1", "2", "5"]].copy()
    log.info("Шаблон stats: %d строк (из mart_mag.stats)", len(df))
    return df

def run_daily_stats(engine, today_str: str, dry_run: bool = False) -> int:
    template_df = build_stats_template(engine, today_str)

    if dry_run:
        log.info("DRY-RUN MART: шаблон построен (%d строк) — в БД не пишем", len(template_df))
        return 0

    tpl  = f"_stats_tpl_{today_str}"
    out  = f"stats_{today_str}"
    sql  = _REPORT_SQL.replace("__TPL__", tpl).replace("__OUT__", out)

    raw_conn = engine.raw_connection()
    try:
        cur = raw_conn.cursor()
        cur.execute("SET statement_timeout = 0")

        cur.execute(f'CREATE TEMP TABLE IF NOT EXISTS "{tpl}" ("1" TEXT, "2" TEXT, "5" TEXT)')
        cur.execute(f'TRUNCATE "{tpl}"')

        buf = io.StringIO()
        for _, r in template_df.iterrows():
            def esc(v):
                return str(v).replace('\\', '\\\\').replace('\t', '\\t').replace('\n', '\\n')
            buf.write('\t'.join(esc(r[c]) for c in ["1", "2", "5"]) + '\n')
        buf.seek(0)
        cur.copy_expert(
            f'COPY "{tpl}" ("1","2","5") FROM STDIN WITH (FORMAT TEXT, NULL \'\\N\')',
            buf
        )
        log.info("COPY шаблона в '%s': %d строк", tpl, len(template_df))

        cur.execute(sql)
        raw_conn.commit()

        cur.execute(f'SELECT COUNT(*) FROM mart_mag."{out}"')
        count = cur.fetchone()[0]
        log.info("MART: создана таблица 'mart_mag.%s' (%d строк)", out, count)

    except BaseException:
        raw_conn.rollback()
        raise
    finally:
        cur.close()
        raw_conn.close()

    return count

def generate_excel(engine, today_str: str) -> str:
    try:
        import xlsxwriter
    except ImportError:
        log.error("xlsxwriter не установлен: pip install xlsxwriter")
        raise

    table_name = f"stats_{today_str}"
    log.info("Excel: читаем таблицу '%s'", table_name)

    with engine.connect() as conn:
        raw_data = pd.read_sql(
            f'SELECT "1","2","3","4","5","6","7","8","9","11","12","14" FROM mart_mag."{table_name}"',
            conn
        ).values.tolist()

    if not raw_data:
        log.warning("Excel: таблица '%s' пуста", table_name)
        return ""

    def sort_key(row):
        try:
            return int(re.sub(r'\D', '', str(row[0]))) if row[0] else 999999
        except Exception:
            return 999999

    data = sorted(raw_data, key=sort_key)

    def clean_number(val):
        if val is None:
            return ""
        if isinstance(val, float) and (val != val or val == float('inf') or val == float('-inf')):
            return ""
        if isinstance(val, str):
            clean = val.replace('\xa0', '').replace(' ', '').strip()
            if re.match(r'^-?\d+$', clean):
                try:
                    return int(clean)
                except ValueError:
                    pass
        return val

    filename = f'Статистика_Магистратура_{today_str}.xlsx'
    wb = xlsxwriter.Workbook(filename)
    ws = wb.add_worksheet('Статистика')

    C_BLUE   = '#DDEBF7'
    C_PEACH  = '#FCE4D6'
    C_WHITE  = '#FFFFFF'
    C_GREY_1 = '#D9D9D9'
    C_GREY_2 = '#EAEAEA'
    C_HEADER = '#EFEFEF'

    fb = {'font_name': 'Arial', 'font_size': 10}
    bb = {'border': 1, 'valign': 'vcenter'}

    title_fmt      = wb.add_format({**fb, 'font_size': 12, 'bold': True, 'align': 'center', 'text_wrap': True})
    hdr_norm_fmt   = wb.add_format({**fb, **bb, 'bold': True, 'align': 'center', 'bg_color': C_HEADER, 'text_wrap': True})
    hdr_vert_fmt   = wb.add_format({**fb, **bb, 'bold': True, 'align': 'center', 'bg_color': C_HEADER, 'text_wrap': True, 'rotation': 90})
    num_row_fmt    = wb.add_format({**fb, **bb, 'align': 'center', 'bg_color': C_GREY_1})

    f_white_c      = wb.add_format({**fb, **bb, 'align': 'center', 'bg_color': C_WHITE})
    f_white_l      = wb.add_format({**fb, **bb, 'align': 'left',   'text_wrap': True, 'bg_color': C_WHITE})
    f_blue_c       = wb.add_format({**fb, **bb, 'align': 'center', 'bg_color': C_BLUE})
    f_blue_money   = wb.add_format({**fb, **bb, 'align': 'center', 'bg_color': C_BLUE,   'num_format': '#,##0'})
    f_peach_c      = wb.add_format({**fb, **bb, 'align': 'center', 'bg_color': C_PEACH})

    l1_c           = wb.add_format({**fb, **bb, 'align': 'center', 'bold': True, 'bg_color': C_GREY_1})
    l1_l           = wb.add_format({**fb, **bb, 'align': 'left',   'bold': True, 'text_wrap': True, 'bg_color': C_GREY_1})
    l1_money       = wb.add_format({**fb, **bb, 'align': 'center', 'bold': True, 'bg_color': C_GREY_1, 'num_format': '#,##0'})

    l2_c           = wb.add_format({**fb, **bb, 'align': 'center', 'bold': True, 'bg_color': C_GREY_2})
    l2_l           = wb.add_format({**fb, **bb, 'align': 'left',   'bold': True, 'text_wrap': True, 'bg_color': C_GREY_2})
    l2_money       = wb.add_format({**fb, **bb, 'align': 'center', 'bold': True, 'bg_color': C_GREY_2, 'num_format': '#,##0'})

    ws.set_column('A:A', 5)
    ws.set_column('B:B', 50)
    ws.set_column('C:H', 10)
    ws.set_column('I:I', 15)
    ws.set_column('J:L', 10)

    cur_year = datetime.now().year
    cur_date = datetime.now().strftime('%d.%m.%Y')

    ws.merge_range('B2:M2',
        f"Статистика заключения и оплаты договоров на обучение  Москва (МАГИСТРАТУРА)\n в {cur_year} году",
        title_fmt)
    ws.set_row(1, 40)

    ws.merge_range('A3:A4', "Номер п/п", hdr_norm_fmt)
    ws.merge_range('B3:B4', "Образовательная программа", hdr_norm_fmt)
    ws.merge_range('C3:M3',
        f"Статистика заключения и оплаты договоров на обучение Москва МАГИСТРАТУРА\n"
        f"(абитуриенты РФ)\n{cur_date}",
        hdr_norm_fmt)
    ws.set_row(2, 60)

    sub_headers = [
        f"ПЛАН\nколичество платных мест {cur_year}",
        "критерии для заключения договоров",
        f"на дату {cur_date}\nколичество договоров, подписанных\nсо стороны абитуриента и НИУ ВШЭ\n"
        f"(с даты объявления критериев для заключения договоров,\nнарастающий итог)",
        "на дату [ВЧЕРА]\nколичество договоров, подписанных со стороны\nабитуриента и НИУ ВШЭ",
        f"прирост на {cur_date}\nколичество договоров, подписанных со стороны\nабитуриента и НИУ ВШЭ",
        f"всего оплачено за весь период,\nв том числе с отсрочкой платежа на дату {cur_date}",
        f"доход по оплаченным договорам на {cur_date}\n(за 1-е полугодие)",
        "количество договоров с использованием кредитных\nсредств",
        "количество договоров с использованием МК",
        "количество оплаченных договоров\nс предоставленной скидкой",
    ]
    for col_num, text_val in enumerate(sub_headers, start=2):
        ws.write(3, col_num, text_val, hdr_vert_fmt)
    ws.set_row(3, 280)

    col_numbers = [1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 14]
    for col_num, val in enumerate(col_numbers):
        ws.write(4, col_num, val, num_row_fmt)

    current_row = 5
    for row_data in data:
        prog_name = str(row_data[1] or "")
        is_l1 = ("Очное обучение" in prog_name or "Очно-заочное" in prog_name or "ИТОГО" in prog_name)
        is_l2 = "Направление подготовки" in prog_name

        for col_index, raw_val in enumerate(row_data):
            cell_val = clean_number(raw_val)

            if is_l1:
                fmt = l1_l if col_index in (1, 12) else (l1_money if col_index == 8 else l1_c)
            elif is_l2:
                fmt = l2_l if col_index in (1, 12) else (l2_money if col_index == 8 else l2_c)
            else:
                if col_index == 1:        fmt = f_white_l
                elif col_index == 2:      fmt = f_blue_c
                elif col_index == 3:      fmt = f_peach_c
                elif col_index in (4,5,6,7,9): fmt = f_blue_c
                elif col_index == 8:      fmt = f_blue_money
                elif col_index == 12:     fmt = f_white_l
                else:                     fmt = f_white_c

            ws.write(current_row, col_index, cell_val if cell_val is not None else "", fmt)

        current_row += 1

    wb.close()
    log.info("Excel: создан файл '%s'", filename)
    return filename
