

import pandas as pd
from sqlalchemy import text
from config import CSV_FILES, COLUMN_RENAMES


def _read_csv(key: str) -> pd.DataFrame:
    path = CSV_FILES[key]
    df = pd.read_csv(path, encoding='utf-8', low_memory=False)
    # Переименовать колонки
    renames = COLUMN_RENAMES.get(key, {})
    df = df.rename(columns=renames)
    # Удалить колонки помеченные '_drop'
    drop_cols = [c for c in df.columns if c == '_drop']
    df = df.drop(columns=drop_cols)
    return df


def extract_applications() -> pd.DataFrame:
    return _read_csv('applications')


def extract_scores() -> pd.DataFrame:
    return _read_csv('scores')


def extract_contracts() -> pd.DataFrame:
    return _read_csv('contracts')


def extract_criteria() -> pd.DataFrame:
    df = _read_csv('criteria')
    # Удалить пустые строки в конце (строки 72-81 в источнике)
    df = df.dropna(how='all')
    return df


def extract_all_csv() -> dict[str, pd.DataFrame]:
    return {
        'applications': extract_applications(),
        'scores':       extract_scores(),
        'contracts':    extract_contracts(),
        'criteria':     extract_criteria(),
    }


def extract_stg_table(engine, table: str) -> pd.DataFrame:
    with engine.connect() as conn:
        return pd.read_sql(f'SELECT * FROM stg_bak."{table}"', conn)


def extract_ods_table(engine, table: str) -> pd.DataFrame:
    with engine.connect() as conn:
        return pd.read_sql(f'SELECT * FROM ods_bak."{table}"', conn)


def extract_dds_fact_current(engine, fact_table: str) -> pd.DataFrame:
    with engine.connect() as conn:
        return pd.read_sql(
            f'SELECT * FROM dds_bak."{fact_table}" WHERE is_current = TRUE',
            conn
        )
