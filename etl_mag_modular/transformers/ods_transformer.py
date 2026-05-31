
import pandas as pd
import numpy as np
import re
from config import today

def _safe_str(val):
    if pd.isna(val) or val == '' or val == 'None':
        return None
    return str(val).strip() if val else None

def _safe_int(val):
    if pd.isna(val) or val == '' or val == 'None':
        return None
    try:
        clean = str(val).replace(' ', '').replace(',', '.')
        return int(float(clean))
    except (ValueError, TypeError):
        return None

def _safe_decimal(val):
    if pd.isna(val) or val == '' or val == 'None':
        return None
    try:
        clean = str(val).replace(' ', '').replace(',', '.')
        return float(clean)
    except (ValueError, TypeError):
        return None

def _safe_bool(val):
    if pd.isna(val) or val == '' or val == 'None':
        return None
    val_str = str(val).strip().lower()
    if val_str in ['да', 'true', '1', 'yes']:
        return True
    elif val_str in ['нет', 'false', '0', 'no']:
        return False
    return None

def _safe_date(val):
    if pd.isna(val) or val == '' or val == 'None':
        return None
    try:
        val_str = str(val).strip()
        try:
            return pd.to_datetime(val_str, format='%d.%m.%Y %H:%M:%S').date()
        except:
            return pd.to_datetime(val_str, format='%d.%m.%Y').date()
    except (ValueError, TypeError):
        return None

def _parse_application_id(val):
    if pd.isna(val) or val == '' or val == 'None':
        return None
    try:
        val_str = str(val).strip()
        match = re.search(r'Заявление\s+(\d+-\d+)', val_str)
        return match.group(1) if match else None
    except:
        return None

def transform_ods_contracts(df):
    df_ods = df.copy()

    df_ods["has_files"] = df_ods.get("has_files", pd.Series()).apply(_safe_bool)
    df_ods["is_active"] = df_ods.get("is_active", pd.Series()).apply(_safe_int)
    df_ods["code"] = df_ods.get("contract_code", pd.Series()).apply(_safe_str)
    df_ods["payment_status"] = df_ods.get("payment_status", pd.Series()).apply(_safe_str)
    df_ods["applicant_name"] = df_ods.get("applicant_name", pd.Series()).apply(_safe_str)
    df_ods["contract_date"] = df_ods.get("contract_date", pd.Series()).apply(_safe_date)
    df_ods["source"] = df_ods.get("source", pd.Series()).apply(_safe_str)
    df_ods["city"] = df_ods.get("city", pd.Series()).apply(_safe_str)
    df_ods["specialization"] = df_ods.get("specialization", pd.Series()).apply(_safe_str)
    df_ods["faculty"] = df_ods.get("faculty", pd.Series()).apply(_safe_str)
    df_ods["program_name"] = df_ods.get("program_name", pd.Series()).apply(_safe_str)
    df_ods["application_id"] = df_ods.get("application_text", pd.Series()).apply(_parse_application_id)
    df_ods["application_text"] = df_ods.get("application_text", pd.Series()).apply(_safe_str)
    df_ods["contract_code"] = df_ods.get("contract_code", pd.Series()).apply(_safe_str)
    df_ods["contract_index"] = df_ods.get("contract_index", pd.Series()).apply(_safe_str)
    df_ods["has_errors"] = df_ods.get("has_errors", pd.Series()).apply(_safe_bool)
    df_ods["submission_type"] = df_ods.get("submission_type", pd.Series()).apply(_safe_str)
    df_ods["payment_method"] = df_ods.get("payment_method", pd.Series()).apply(_safe_str)
    df_ods["party_count"] = df_ods.get("party_count", pd.Series()).apply(_safe_int)
    df_ods["customer_type"] = df_ods.get("customer_type", pd.Series()).apply(_safe_str)
    df_ods["ip_status"] = df_ods.get("ip_status", pd.Series()).apply(_safe_str)
    df_ods["start_date"] = df_ods.get("start_date", pd.Series()).apply(_safe_date)
    df_ods["end_date"] = df_ods.get("end_date", pd.Series()).apply(_safe_date)
    df_ods["comments"] = df_ods.get("comments", pd.Series()).apply(_safe_str)
    df_ods["responsible"] = df_ods.get("responsible", pd.Series()).apply(_safe_str)
    df_ods["discount_percent"] = df_ods.get("discount_percent", pd.Series()).apply(_safe_decimal)
    df_ods["link"] = df_ods.get("link", pd.Series()).apply(_safe_str)
    df_ods["semester_cost"] = df_ods.get("semester_cost", pd.Series()).apply(_safe_decimal)
    df_ods["total_sum"] = df_ods.get("total_sum", pd.Series()).apply(_safe_decimal)
    df_ods["customer_name"] = df_ods.get("customer_name", pd.Series()).apply(_safe_str)
    df_ods["customer_email"] = df_ods.get("customer_email", pd.Series()).apply(_safe_str)
    df_ods["email"] = df_ods.get("email", pd.Series()).apply(_safe_str)

    df_ods["applicant_code"] = df_ods.get("applicant_code", pd.Series()).apply(_safe_str)

    ods_cols = [
        "code", "has_files", "is_active", "contract_code", "applicant_code", "payment_status",
        "applicant_name", "contract_date", "source", "city", "specialization", "faculty",
        "program_name", "application_id", "application_text", "contract_index", "has_errors",
        "submission_type", "payment_method", "party_count", "customer_type", "ip_status",
        "start_date", "end_date", "comments", "responsible", "discount_percent", "link",
        "semester_cost", "total_sum", "customer_name", "customer_email", "email"
    ]

    result_cols = [col for col in ods_cols if col in df_ods.columns]
    result = df_ods[result_cols].drop_duplicates(subset=['code'], keep='last')

    return result[result['code'].notna()]

def transform_ods_payment_schedules(df):
    df_ods = df.copy()

    df_ods = df_ods.rename(columns={"schedule_code": "schedule_code"})
    df_ods["owner"] = df_ods.get("owner", pd.Series()).apply(_safe_str)
    df_ods["semester_cost"] = df_ods.get("semester_cost", pd.Series()).apply(_safe_decimal)
    df_ods["applicant_name"] = df_ods.get("applicant_name", pd.Series()).apply(_safe_str)
    df_ods["applicant_code"] = df_ods.get("applicant_code", pd.Series()).apply(_safe_str)
    df_ods["discount_text"] = df_ods.get("discount_text", pd.Series()).apply(_safe_str)
    df_ods["discount_value"] = df_ods.get("discount_value", pd.Series()).apply(_safe_decimal)
    df_ods["payment_status"] = df_ods.get("payment_status", pd.Series()).apply(_safe_str)
    df_ods["reg_number"] = df_ods.get("reg_number", pd.Series()).apply(_safe_str)
    df_ods["discount_percent"] = df_ods.get("discount_percent", pd.Series()).apply(_safe_decimal)

    return df_ods[[
        "schedule_code", "owner", "semester_cost", "applicant_name", "applicant_code",
        "discount_text", "discount_value", "payment_status", "reg_number", "discount_percent"
    ]].drop_duplicates(subset=['schedule_code'], keep='last')

def transform_ods_payments(df):
    df_ods = df.copy()

    df_ods["payment_id"] = df_ods.get("payment_id", pd.Series()).apply(_safe_str)
    df_ods["deletion_mark"] = df_ods.get("deletion_mark", pd.Series()).apply(_safe_bool)
    df_ods["payment_date_upload"] = df_ods.get("payment_date_upload", pd.Series()).apply(_safe_date)
    df_ods["payment_amount"] = df_ods.get("payment_amount", pd.Series()).apply(_safe_decimal)
    df_ods["contract_code"] = df_ods.get("contract_code_ref", pd.Series()).apply(_safe_str)
    df_ods["payment_name"] = df_ods.get("payment_name", pd.Series()).apply(_safe_str)
    df_ods["specialization"] = df_ods.get("specialization_payment", pd.Series()).apply(_safe_str)
    df_ods["applicant_code"] = df_ods.get("applicant_code", pd.Series()).apply(_safe_str)
    df_ods["has_security_payment"] = df_ods.get("has_security_payment", pd.Series()).apply(_safe_bool)
    df_ods["applicant_name"] = df_ods.get("applicant_name", pd.Series()).apply(_safe_str)
    df_ods["payment_date"] = df_ods.get("payment_date", pd.Series()).apply(_safe_date)
    df_ods["comments"] = df_ods.get("payment_comments", pd.Series()).apply(_safe_str)
    df_ods["payment_type"] = df_ods.get("payment_type", pd.Series()).apply(_safe_str)
    df_ods["responsible"] = df_ods.get("payment_responsible", pd.Series()).apply(_safe_str)

    return df_ods[[
        "payment_id", "deletion_mark", "payment_date_upload", "payment_amount", "contract_code",
        "payment_name", "specialization", "applicant_code", "has_security_payment", "applicant_name",
        "payment_date", "comments", "payment_type", "responsible"
    ]].drop_duplicates(subset=['payment_id'], keep='last')

def transform_ods_criteria(df):
    df_ods = df.copy()

    df_ods["program_name"] = df_ods.get("program_name", pd.Series()).apply(_safe_str)
    df_ods["criteria_id"] = df_ods.get("criteria_id", pd.Series()).apply(_safe_int)

    return df_ods[["program_name", "criteria_id"]].drop_duplicates()

def transform_ods_admission_plan(df):
    df_ods = df.copy()

    df_ods["program_name"] = df_ods.get("program_name", pd.Series()).apply(_safe_str)
    df_ods["budget_seats"] = df_ods.get("budget_seats", pd.Series()).apply(_safe_int)
    df_ods["contract_seats"] = df_ods.get("contract_seats", pd.Series()).apply(_safe_int)

    return df_ods[["program_name", "budget_seats", "contract_seats"]].drop_duplicates(subset=['program_name'], keep='last')
