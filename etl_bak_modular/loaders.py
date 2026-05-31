

import io
import logging
import pandas as pd
from datetime import date
from sqlalchemy import text
from tqdm import tqdm

log = logging.getLogger('etl_bak')

BATCH_SIZE = 5_000

def _df_to_tsv(df: pd.DataFrame) -> io.StringIO:
    buf = io.StringIO()
    for row in df.itertuples(index=False, name=None):
        parts = []
        for v in row:
            if v is None or v is pd.NA or (isinstance(v, float) and pd.isna(v)):
                parts.append('\\N')
            elif isinstance(v, float) and v.is_integer():
                parts.append(str(int(v)))
            else:
                s = str(v)
                s = (s.replace('\\', '\\\\')
                      .replace('\t', '\\t')
                      .replace('\n', '\\n')
                      .replace('\r', '\\r'))
                parts.append(s)
        buf.write('\t'.join(parts) + '\n')
    buf.seek(0)
    return buf

def _copy_upsert(raw_conn, schema: str, table: str, df: pd.DataFrame,
                 conflict_str: str, update_set: str, label: str):
    cols     = list(df.columns)
    col_list = ', '.join(f'"{c}"' for c in cols)
    prefix   = schema.split('_')[0]
    tmp      = f'_tmp_{prefix}_{table}'
    total    = len(df)

    cur = raw_conn.cursor()
    try:
        cur.execute("SET statement_timeout = 0")
        cur.execute("SET lock_timeout = '15s'")

        cur.execute(f'DROP TABLE IF EXISTS "{tmp}"')
        cur.execute(
            f'CREATE TEMP TABLE "{tmp}" '
            f'AS SELECT * FROM {schema}."{table}" WHERE FALSE'
        )

        cur.copy_expert(
            f'COPY "{tmp}" ({col_list}) FROM STDIN WITH (FORMAT TEXT, NULL \'\\N\')',
            _df_to_tsv(df)
        )
        cur.execute(f'ALTER TABLE "{tmp}" DROP COLUMN IF EXISTS _etl_rn')
        cur.execute(f'ALTER TABLE "{tmp}" ADD COLUMN _etl_rn SERIAL')
        log.info("COPY в temp '%s': %d строк", tmp, total)

        if update_set:
            insert_tpl = (
                f'INSERT INTO {schema}."{table}" ({col_list}) '
                f'SELECT {col_list} FROM "{tmp}" ORDER BY _etl_rn LIMIT {{limit}} OFFSET {{offset}} '
                f'ON CONFLICT ({conflict_str}) DO UPDATE SET {update_set}'
            )
        else:
            insert_tpl = (
                f'INSERT INTO {schema}."{table}" ({col_list}) '
                f'SELECT {col_list} FROM "{tmp}" ORDER BY _etl_rn LIMIT {{limit}} OFFSET {{offset}} '
                f'ON CONFLICT ({conflict_str}) DO NOTHING'
            )

        with tqdm(desc=label, total=total, unit='rows', ncols=80) as bar:
            for offset in range(0, total, BATCH_SIZE):
                limit = min(BATCH_SIZE, total - offset)
                cur.execute(insert_tpl.format(limit=limit, offset=offset))
                bar.update(limit)

        raw_conn.commit()

    except BaseException:
        try:
            raw_conn.rollback()
        except Exception:
            pass
        raise
    finally:
        try:
            cur.close()
        except Exception:
            pass

def _get_raw_conn(engine):
    return engine.raw_connection()

def _safe_close(raw_conn):
    try:
        raw_conn.close()
    except Exception:
        pass

def append_to_stg(engine, df: pd.DataFrame, table: str, pk_col: str, dry_run: bool = False) -> int:
    if df.empty:
        return 0
    total = len(df)
    
    with engine.connect() as conn:
        existing_pks = pd.read_sql(f'SELECT "{pk_col}" FROM stg_bak."{table}"', conn)
    
    new_records = df[~df[pk_col].isin(existing_pks[pk_col])]
    

    if dry_run:
        log.info("STG: %s → %d строк [dry-run]", table, total)
        return total

    raw_conn = _get_raw_conn(engine)
    try:
        _copy_upsert(raw_conn, 'stg_bak', table, df,
                     conflict_str=f'"{pk_col}"',
                     update_set='',
                     label=f"STG {table}")
    finally:
        _safe_close(raw_conn)

    return total

def upsert_ods(engine, df: pd.DataFrame, table: str, nat_key: str, dry_run: bool = False) -> int:
    if df.empty:
        return 0
    total = len(df)
    if dry_run:
        log.info("ODS: %s → %d строк [dry-run]", table, total)
        return total

    cols        = list(df.columns)
    update_cols = [c for c in cols if c != nat_key]
    set_clause  = ', '.join(f'"{c}" = EXCLUDED."{c}"' for c in update_cols)
    if set_clause:
        set_clause += ', updated_at = NOW()'

    raw_conn = _get_raw_conn(engine)
    try:
        _copy_upsert(raw_conn, 'ods_bak', table, df,
                     conflict_str=f'"{nat_key}"',
                     update_set=set_clause,
                     label=f"ODS  {table}")
    finally:
        _safe_close(raw_conn)

    return total

def upsert_dim(engine, df: pd.DataFrame, table: str, conflict_cols: list[str], dry_run: bool = False) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    total = len(df)
    if dry_run:
        log.info("DDS dim: %s → %d строк [dry-run]", table, total)
        return pd.DataFrame()

    cols         = list(df.columns)
    conflict_str = ', '.join(f'"{c}"' for c in conflict_cols)
    update_cols  = [c for c in cols if c not in conflict_cols]
    set_clause   = ', '.join(f'"{c}" = EXCLUDED."{c}"' for c in update_cols)
    if set_clause:
        set_clause += ', updated_at = NOW()'

    raw_conn = _get_raw_conn(engine)
    try:
        _copy_upsert(raw_conn, 'dds_bak', table, df,
                     conflict_str=conflict_str,
                     update_set=set_clause,
                     label=f"DDS  {table}")
    finally:
        _safe_close(raw_conn)

    with engine.connect() as conn:
        return pd.read_sql(f'SELECT * FROM dds_bak."{table}"', conn)

def apply_scd2(engine, to_insert: pd.DataFrame, to_close: pd.DataFrame,
               fact_table: str, pk_col: str, close_date: date, dry_run: bool = False) -> int:

    if to_close.empty and to_insert.empty:
        return 0

    if dry_run:
        if not to_close.empty:
            log.info("SCD2 %s: закрыть %d [dry-run]", fact_table, len(to_close))
        if not to_insert.empty:
            log.info("SCD2 %s: вставить %d [dry-run]", fact_table, len(to_insert))
        return len(to_insert)

    inserted = 0
    raw_conn = _get_raw_conn(engine)
    cur = raw_conn.cursor()
    try:
        cur.execute("SET statement_timeout = 0")
        cur.execute("SET lock_timeout = '15s'")

        if not to_close.empty:
            ids = to_close[pk_col].tolist()
            log.info("SCD2 %s: закрываем %d старых версий...", fact_table, len(ids))
            cur.execute(
                f'UPDATE dds_bak."{fact_table}" '
                f'SET valid_to = %s, is_current = FALSE '
                f'WHERE "{pk_col}" = ANY(%s)',
                (close_date, ids)
            )
            log.info("SCD2 %s: закрыто ✓", fact_table)

        if not to_insert.empty:
            total    = len(to_insert)
            cols     = list(to_insert.columns)
            col_list = ', '.join(f'"{c}"' for c in cols)
            tmp      = f'_tmp_dds_{fact_table}'

            cur.execute(
                f'CREATE TEMP TABLE IF NOT EXISTS "{tmp}" '
                f'AS SELECT * FROM dds_bak."{fact_table}" WHERE FALSE'
            )
            cur.execute(f'TRUNCATE "{tmp}"')
            cur.copy_expert(
                f'COPY "{tmp}" ({col_list}) FROM STDIN WITH (FORMAT TEXT, NULL \'\\N\')',
                _df_to_tsv(to_insert)
            )
            cur.execute(f'ALTER TABLE "{tmp}" DROP COLUMN IF EXISTS _etl_rn')
            cur.execute(f'ALTER TABLE "{tmp}" ADD COLUMN _etl_rn SERIAL')
            log.info("SCD2 %s: COPY в temp %d строк", fact_table, total)

            with tqdm(desc=f"DDS  {fact_table}", total=total, unit='rows', ncols=80) as bar:
                for offset in range(0, total, BATCH_SIZE):
                    limit = min(BATCH_SIZE, total - offset)
                    cur.execute(
                        f'INSERT INTO dds_bak."{fact_table}" ({col_list}) '
                        f'SELECT {col_list} FROM "{tmp}" ORDER BY _etl_rn LIMIT {limit} OFFSET {offset}'
                    )
                    bar.update(limit)

            inserted = total

        raw_conn.commit()

    except BaseException:
        try:
            raw_conn.rollback()
        except Exception:
            pass
        raise
    finally:
        try:
            cur.close()
        except Exception:
            pass
        _safe_close(raw_conn)

    return inserted
