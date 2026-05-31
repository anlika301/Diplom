
import io
import logging
import pandas as pd
from datetime import date
from sqlalchemy import text
from tqdm import tqdm
from config import BATCH_SIZE

log = logging.getLogger('etl_mag')

def _parse_table(full_name):
    parts = full_name.split('.', 1)
    return parts[0], parts[1]

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
                 conflict_str, update_set: str, label: str):
    cols     = list(df.columns)
    col_list = ', '.join(f'"{c}"' for c in cols)
    prefix   = schema.split('_')[0]
    tmp      = f'_tmp_{prefix}_{table}'
    total    = len(df)

    cur = raw_conn.cursor()
    try:
        cur.execute("SET statement_timeout = 0")
        cur.execute("SET lock_timeout = '15s'")

        cur.execute(
            f'CREATE TEMP TABLE IF NOT EXISTS "{tmp}" '
            f'AS SELECT {col_list} FROM {schema}."{table}" WHERE FALSE'
        )
        cur.execute(f'TRUNCATE "{tmp}"')

        cur.copy_expert(
            f'COPY "{tmp}" ({col_list}) FROM STDIN WITH (FORMAT TEXT, NULL \'\\N\')',
            _df_to_tsv(df)
        )
        cur.execute(f'ALTER TABLE "{tmp}" ADD COLUMN _etl_rn SERIAL')
        log.info("COPY в temp '%s': %d строк", tmp, total)

        base = (
            f'INSERT INTO {schema}."{table}" ({col_list}) '
            f'SELECT {col_list} FROM "{tmp}" ORDER BY _etl_rn LIMIT {{limit}} OFFSET {{offset}}'
        )

        if conflict_str is None:
            insert_tpl = base
        elif conflict_str == '':
            insert_tpl = base + ' ON CONFLICT DO NOTHING'
        elif update_set:
            insert_tpl = base + f' ON CONFLICT ({conflict_str}) DO UPDATE SET {update_set}'
        else:
            insert_tpl = base + f' ON CONFLICT ({conflict_str}) DO NOTHING'

        with tqdm(desc=label, total=total, unit='rows', ncols=80) as bar:
            for offset in range(0, total, BATCH_SIZE):
                limit = min(BATCH_SIZE, total - offset)
                cur.execute(insert_tpl.format(limit=limit, offset=offset))
                bar.update(limit)

        raw_conn.commit()

    except BaseException:
        raw_conn.rollback()
        raise
    finally:
        cur.close()

def _get_raw_conn(engine):
    return engine.raw_connection()

def append_to_stg(engine, df: pd.DataFrame, full_table: str) -> int:
    if df.empty:
        return 0

    schema, table = _parse_table(full_table)
    raw_conn = _get_raw_conn(engine)
    try:
        _copy_upsert(raw_conn, schema, table, df,
                     conflict_str='',
                     update_set='',
                     label=f"STG  {table}")
    finally:
        raw_conn.close()

    return len(df)

def upsert_ods(engine, df: pd.DataFrame, full_table: str, pk_cols) -> int:
    if df.empty:
        return 0

    schema, table = _parse_table(full_table)

    if isinstance(pk_cols, str):
        pk_cols = [pk_cols]

    conflict_str = ', '.join(f'"{c}"' for c in pk_cols)
    update_cols  = [c for c in df.columns if c not in pk_cols]
    set_clause   = ', '.join(f'"{c}" = EXCLUDED."{c}"' for c in update_cols)
    if set_clause:
        set_clause += ', updated_at = NOW()'

    raw_conn = _get_raw_conn(engine)
    try:
        _copy_upsert(raw_conn, schema, table, df,
                     conflict_str=conflict_str,
                     update_set=set_clause,
                     label=f"ODS  {table}")
    finally:
        raw_conn.close()

    return len(df)

def upsert_dim(engine, df: pd.DataFrame, full_table: str, conflict_cols: list) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    schema, table = _parse_table(full_table)

    conflict_str = ', '.join(f'"{c}"' for c in conflict_cols)
    update_cols  = [c for c in df.columns if c not in conflict_cols]
    set_clause   = ', '.join(f'"{c}" = EXCLUDED."{c}"' for c in update_cols)
    if set_clause:
        set_clause += ', updated_at = NOW()'

    raw_conn = _get_raw_conn(engine)
    try:
        _copy_upsert(raw_conn, schema, table, df,
                     conflict_str=conflict_str,
                     update_set=set_clause,
                     label=f"DDS  {table}")
    finally:
        raw_conn.close()

    with engine.connect() as conn:
        return pd.read_sql(f'SELECT * FROM {schema}."{table}"', conn)

def apply_scd2(engine, full_table: str, new_df: pd.DataFrame,
               tracked_fields: list, pk_col: str) -> int:
    today_date = date.today()

    if new_df.empty:
        log.info("SCD2 %s: пустой DataFrame, пропуск", full_table)
        return 0

    new_df = new_df.reset_index(drop=True)

    schema, table = _parse_table(full_table)

    with engine.connect() as conn:
        try:
            existing = pd.read_sql(
                f'SELECT * FROM {schema}."{table}" WHERE is_current = TRUE',
                conn
            )
        except Exception:
            existing = pd.DataFrame()

    if existing.empty:
        to_insert = new_df.copy()
        log.info("SCD2 %s: первая загрузка, %d записей", full_table, len(to_insert))
    else:
        existing_pk = existing[[pk_col] + [f for f in tracked_fields if f in existing.columns]].copy()
        existing_pk = existing_pk.rename(columns={
            pk_col: f'{pk_col}__existing',
            **{f: f'{f}__old' for f in tracked_fields if f in existing.columns}
        })

        merged = new_df.merge(
            existing_pk,
            left_on=pk_col,
            right_on=f'{pk_col}__existing',
            how='left'
        )

        to_close_pks = []
        insert_indices = []

        for idx, row in merged.iterrows():
            is_new_record = pd.isna(row.get(f'{pk_col}__existing'))

            if is_new_record:
                insert_indices.append(idx)
            else:
                changed = False
                for f in tracked_fields:
                    old_col = f'{f}__old'
                    old_val = row.get(old_col)
                    new_val = row[f]
                    old_str = str(old_val) if pd.notna(old_val) else None
                    new_str = str(new_val) if pd.notna(new_val) else None
                    if old_str != new_str:
                        changed = True
                        break
                if changed:
                    to_close_pks.append(row[pk_col])
                    insert_indices.append(idx)

        if to_close_pks:
            with engine.begin() as conn:
                conn.execute(text(
                    f'UPDATE {schema}."{table}" '
                    f'SET valid_to = :today, is_current = FALSE '
                    f'WHERE "{pk_col}" = ANY(:ids) AND is_current = TRUE'
                ), {'today': today_date, 'ids': to_close_pks})
            log.info("SCD2 %s: закрыто %d старых версий", full_table, len(to_close_pks))

        if insert_indices:
            to_insert = new_df.loc[insert_indices].copy()
        else:
            to_insert = pd.DataFrame(columns=new_df.columns)

    if to_insert.empty:
        log.info("SCD2 %s: нет изменений", full_table)
        return 0

    raw_conn = _get_raw_conn(engine)
    try:
        _copy_upsert(raw_conn, schema, table, to_insert,
                     conflict_str=None,
                     update_set='',
                     label=f"SCD2 {table}")
    finally:
        raw_conn.close()

    log.info("SCD2 %s: вставлено %d новых записей", full_table, len(to_insert))
    return len(to_insert)

def read_staging_table(engine, full_table: str) -> pd.DataFrame:
    query = f"SELECT * FROM {full_table}"
    return pd.read_sql(query, engine)
