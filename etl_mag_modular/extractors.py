
import pandas as pd

def extract_ods_contracts(engine):
    query = """
    SELECT
        code,
        has_files,
        is_active,
        contract_code,
        applicant_code,
        payment_status,
        applicant_name,
        contract_date,
        source,
        city,
        specialization,
        faculty,
        program_name,
        application_id,
        discount_percent,
        semester_cost,
        total_sum,
        email
    FROM ods_mag.contracts
    WHERE code IS NOT NULL
    ORDER BY code
    """
    return pd.read_sql(query, engine)

def extract_ods_payment_schedules(engine):
    query = """
    SELECT
        schedule_code,
        owner,
        applicant_code,
        discount_value,
        payment_status,
        discount_percent
    FROM ods_mag.payment_schedules
    WHERE schedule_code IS NOT NULL
    ORDER BY schedule_code
    """
    return pd.read_sql(query, engine)

def extract_ods_payments(engine):
    query = """
    SELECT
        payment_id,
        contract_code,
        payment_date,
        payment_amount,
        applicant_code,
        payment_name,
        has_security_payment
    FROM ods_mag.payments
    WHERE payment_id IS NOT NULL
    ORDER BY payment_id
    """
    return pd.read_sql(query, engine)

def extract_ods_criteria(engine):
    query = """
    SELECT
        program_name,
        criteria_id
    FROM ods_mag.criteria
    WHERE program_name IS NOT NULL
    ORDER BY program_name, criteria_id
    """
    return pd.read_sql(query, engine)

def extract_ods_admission_plan(engine):
    query = """
    SELECT
        program_name,
        budget_seats,
        contract_seats
    FROM ods_mag.admission_plan
    WHERE program_name IS NOT NULL
    ORDER BY program_name
    """
    return pd.read_sql(query, engine)

def extract_dds_dim_applicants(engine):
    query = "SELECT applicant_id, applicant_code FROM dds_mag.dim_applicants ORDER BY applicant_id"
    return pd.read_sql(query, engine)

def extract_dds_dim_programs(engine):
    query = "SELECT program_id, program_name, specialization, faculty FROM dds_mag.dim_programs ORDER BY program_id"
    return pd.read_sql(query, engine)

def extract_dds_fact_contracts_current(engine):
    query = """
    SELECT
        contract_id,
        applicant_code,
        program_name,
        ods_contract_code,
        payment_status,
        discount_percent,
        semester_cost,
        valid_from,
        valid_to,
        is_current
    FROM dds_mag.fact_contracts
    WHERE is_current = TRUE
    ORDER BY contract_id
    """
    return pd.read_sql(query, engine)
