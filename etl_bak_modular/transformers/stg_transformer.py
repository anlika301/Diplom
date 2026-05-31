
import pandas as pd
from datetime import date

def _add_stg_meta(df: pd.DataFrame, source_file: str, load_date: date) -> pd.DataFrame:
    df = df.copy()
    df['load_date']   = load_date
    df['source_file'] = source_file
    return df

def transform_applications(df: pd.DataFrame, load_date: date,
                            source_file: str = 'application_bak_rows.csv') -> pd.DataFrame:
    return _add_stg_meta(df, source_file, load_date)

def transform_scores(df: pd.DataFrame, load_date: date,
                     source_file: str = 'ball_bak_rows.csv') -> pd.DataFrame:
    return _add_stg_meta(df, source_file, load_date)

def transform_contracts(df: pd.DataFrame, load_date: date,
                        source_file: str = 'dogovor_bak_rows.csv') -> pd.DataFrame:
    return _add_stg_meta(df, source_file, load_date)

def transform_criteria(df: pd.DataFrame, load_date: date,
                       source_file: str = 'kriterii_bak_rows.csv') -> pd.DataFrame:
    return _add_stg_meta(df, source_file, load_date)
