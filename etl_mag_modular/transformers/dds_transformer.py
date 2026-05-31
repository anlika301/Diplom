
import re
import pandas as pd
import numpy as np
from config import today

_JUNK_PATTERN = r'(?i)^(всего|итого)\b'

def normalize_program_name(series):
    s = series.copy().astype(str)
    s = s.str.replace(r'\s*/\s*[A-Za-z].*', '', regex=True)
    s = s.str.replace(r'\s*\(он[лл]айн\)', '', regex=True, flags=re.IGNORECASE)
    s = s.str.replace(r'\s*\(online\)', '', regex=True, flags=re.IGNORECASE)
    s = s.str.strip()
    s[series.isna()] = None
    return s

def is_junk_program(series):
    return series.str.contains(_JUNK_PATTERN, regex=True, na=False)

def build_dim_applicants(ods_contracts):
    applicants = ods_contracts[[
        'applicant_code', 'applicant_name', 'email'
    ]].drop_duplicates(subset=['applicant_code'], keep='last').copy()
    applicants = applicants[applicants['applicant_code'].notna()]
    applicants = applicants.rename(columns={'applicant_name': 'full_name'})
    return applicants[['applicant_code', 'full_name', 'email']]

def build_dim_programs(ods_contracts, ods_criteria=None, ods_plan=None):
    from_contracts = ods_contracts[['specialization', 'program_name', 'faculty']].copy()
    from_contracts['specialization'] = normalize_program_name(from_contracts['specialization'])
    from_contracts = from_contracts[from_contracts['specialization'].notna()]
    from_contracts = from_contracts.rename(columns={'specialization': 'program_name', 'program_name': 'specialization'})
    from_contracts = from_contracts[['program_name', 'specialization', 'faculty']]

    extra = []
    if ods_criteria is not None:
        crit = ods_criteria[['program_name']].copy()
        crit['program_name'] = normalize_program_name(crit['program_name'])
        crit = crit[crit['program_name'].notna() & ~is_junk_program(crit['program_name'])]
        crit['specialization'] = None
        crit['faculty'] = None
        extra.append(crit[['program_name', 'specialization', 'faculty']])

    if ods_plan is not None:
        plan = ods_plan[['program_name']].copy()
        plan['program_name'] = normalize_program_name(plan['program_name'])
        plan = plan[plan['program_name'].notna() & ~is_junk_program(plan['program_name'])]
        plan['specialization'] = None
        plan['faculty'] = None
        extra.append(plan[['program_name', 'specialization', 'faculty']])

    all_programs = pd.concat([from_contracts] + extra, ignore_index=True)
    all_programs = all_programs.drop_duplicates(subset=['program_name'], keep='first')
    return all_programs

def build_dim_criteria(ods_criteria, dim_programs):
    criteria = ods_criteria[ods_criteria['program_name'].notna()].copy()
    criteria['program_name'] = normalize_program_name(criteria['program_name'])
    criteria = criteria[~is_junk_program(criteria['program_name'])]
    return criteria[['program_name', 'criteria_id']].drop_duplicates()

def build_dim_admission_plans(ods_plan, dim_programs):
    plan = ods_plan[ods_plan['program_name'].notna()].copy()
    plan['program_name'] = normalize_program_name(plan['program_name'])
    plan = plan[~is_junk_program(plan['program_name'])]
    return plan[['program_name', 'budget_seats', 'contract_seats']].drop_duplicates(
        subset=['program_name'], keep='last'
    )

def build_fact_contracts(ods_contracts, dim_applicants, dim_programs):
    contracts = ods_contracts[[
        'code', 'applicant_code', 'specialization', 'application_id',
        'has_files', 'is_active', 'payment_status', 'discount_percent',
        'semester_cost', 'total_sum', 'contract_date'
    ]].copy()
    contracts = contracts.rename(columns={'specialization': 'program_name'})
    contracts['program_name'] = normalize_program_name(contracts['program_name'])
    contracts = contracts.merge(dim_applicants[['applicant_code']], on='applicant_code', how='left')
    contracts = contracts.merge(dim_programs[['program_name']], on='program_name', how='left')
    contracts = contracts[contracts['applicant_code'].notna() & contracts['program_name'].notna()]
    contracts = contracts.rename(columns={'code': 'ods_contract_code'})
    contracts['valid_from'] = today
    contracts['valid_to'] = None
    contracts['is_current'] = True
    contracts['load_date'] = today
    return contracts[[
        'ods_contract_code', 'applicant_code', 'program_name', 'application_id',
        'has_files', 'is_active', 'payment_status', 'discount_percent',
        'semester_cost', 'total_sum', 'contract_date', 'valid_from', 'valid_to', 'is_current', 'load_date'
    ]]

def build_fact_payment_schedules(ods_schedules, dim_applicants):
    schedules = ods_schedules[[
        'schedule_code', 'applicant_code', 'owner', 'discount_value', 'payment_status'
    ]].copy()
    schedules = schedules.merge(dim_applicants[['applicant_code']], on='applicant_code', how='left')
    schedules = schedules[schedules['applicant_code'].notna()]
    schedules['valid_from'] = today
    schedules['valid_to'] = None
    schedules['is_current'] = True
    schedules['load_date'] = today
    return schedules[[
        'schedule_code', 'applicant_code', 'owner', 'discount_value',
        'payment_status', 'valid_from', 'valid_to', 'is_current', 'load_date'
    ]]

def build_fact_payments(ods_payments, dim_applicants):
    payments = ods_payments[[
        'payment_id', 'applicant_code', 'contract_code', 'payment_date',
        'payment_amount', 'has_security_payment', 'payment_name'
    ]].copy()
    payments = payments.merge(dim_applicants[['applicant_code']], on='applicant_code', how='left')
    payments = payments[payments['applicant_code'].notna()]
    payments['valid_from'] = today
    payments['valid_to'] = None
    payments['is_current'] = True
    payments['load_date'] = today
    return payments[[
        'payment_id', 'applicant_code', 'contract_code', 'payment_date',
        'payment_amount', 'has_security_payment', 'payment_name',
        'valid_from', 'valid_to', 'is_current', 'load_date'
    ]]
