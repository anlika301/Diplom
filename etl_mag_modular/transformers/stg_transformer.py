
from config import today

def transform_stg_contracts(df):
    df_copy = df.copy()
    df_copy["load_date"] = today
    df_copy["source_file"] = "dogovor_rows.csv"
    return df_copy

def transform_stg_payment_schedules(df):
    df_copy = df.copy()
    df_copy["load_date"] = today
    df_copy["source_file"] = "grafics_rows.csv"
    return df_copy

def transform_stg_payments(df):
    df_copy = df.copy()
    df_copy["load_date"] = today
    df_copy["source_file"] = "kvitancii_rows.csv"
    return df_copy

def transform_stg_criteria(df):
    df_copy = df.copy()
    df_copy["load_date"] = today
    df_copy["source_file"] = "crit_mag_rows.csv"
    return df_copy

def transform_stg_admission_plan(df):
    df_copy = df.copy()
    df_copy["load_date"] = today
    df_copy["source_file"] = "plan_rows.csv"
    return df_copy
