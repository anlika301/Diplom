
import re
import difflib
import random
import unicodedata
import pandas as pd
from datetime import date, timedelta

_KNOWN_PAYMENT_STATUSES = [
    'Оплачен по квитанциям',
    'Ожидает оплаты',
    'Оплачен',
    'Оплачен частично',
]

_CONTRACT_DATE_MIN = date.fromisoformat('2025-06-20')
_CONTRACT_DATE_MAX = date.fromisoformat('2025-08-03')

def _normalize_payment_status(series: pd.Series) -> pd.Series:
    def _parse(v):
        if pd.isna(v) or str(v).strip() == '':
            return None
        cleaned = ''.join(
            c for c in str(v).strip()
            if ord(c) != 0xFFFD and unicodedata.category(c) != 'Co'
        )
        matches = difflib.get_close_matches(cleaned, _KNOWN_PAYMENT_STATUSES, n=1, cutoff=0.75)
        return matches[0] if matches else cleaned
    return series.apply(_parse)

def _safe_int(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors='coerce').astype('Int64')

def _safe_decimal(series: pd.Series) -> pd.Series:
    def _parse(v):
        if pd.isna(v) or str(v).strip() in ('', '-', 'nan'):
            return None
        v = re.sub(r'\s', '', str(v)).replace(',', '.')
        try:
            return float(v)
        except ValueError:
            return None
    return series.apply(_parse)

def _safe_bool(series: pd.Series) -> pd.Series:
    mapping = {'да': True, 'нет': False, 'yes': True, 'no': False, '1': True, '0': False}
    def _parse(v):
        if pd.isna(v) or str(v).strip() == '':
            return None
        return mapping.get(str(v).strip().lower())
    return series.apply(_parse)

def _safe_str(series: pd.Series, maxlen: int = None) -> pd.Series:
    def _parse(v):
        if pd.isna(v) or str(v).strip() == '':
            return None
        s = ''.join(
            c for c in str(v).strip()
            if ord(c) != 0xFFFD and unicodedata.category(c) != 'Co'
        )
        return s[:maxlen] if maxlen else s
    return series.apply(_parse)

def _parse_contract_date(v) -> date:
    if pd.isna(v) or str(v).strip() in ('', 'nan', 'None'):
        delta = (_CONTRACT_DATE_MAX - _CONTRACT_DATE_MIN).days
        return _CONTRACT_DATE_MIN + timedelta(days=random.randint(0, delta))
    try:
        return pd.to_datetime(str(v)).date()
    except Exception:
        delta = (_CONTRACT_DATE_MAX - _CONTRACT_DATE_MIN).days
        return _CONTRACT_DATE_MIN + timedelta(days=random.randint(0, delta))

def _normalize_id_application(series: pd.Series) -> pd.Series:
    def _parse(v):
        if pd.isna(v) or str(v).strip() in ('', 'nan', 'None'):
            return None
        s = str(v).strip()
        if s.startswith('00-'):
            numeric = s[3:]
            if numeric.isdigit():
                return f"00-{int(numeric):09d}"
            return s
        try:
            num = int(float(s))
            return f"00-{num:09d}"
        except (ValueError, OverflowError):
            return s
    return series.apply(_parse)

def transform_applications(df: pd.DataFrame, load_date: date) -> pd.DataFrame:
    out = pd.DataFrame()
    out['app_id']        = _normalize_id_application(df.get('id', pd.Series(dtype=str)))
    out['load_date']     = load_date
    out['full_name']     = _safe_str(df.get('full_name'))
    out['code_applicant']= _safe_str(df.get('code_applicant'), 50)
    out['city']          = _safe_str(df.get('city'), 100)
    out['specialization']= _safe_str(df.get('specialization'))
    out['program']       = _safe_str(df.get('program'))
    out['priority']      = _safe_int(df.get('priority', pd.Series(dtype=str)))
    out['reg_number']    = _safe_str(df.get('reg_number'), 50)
    out['uniq_code']     = _safe_str(df.get('uniq_code'))
    out['sspvo_status']  = _safe_str(df.get('sspvo_status'))
    out = out.dropna(subset=['app_id'])
    return out.drop_duplicates(subset=['app_id'])

def transform_scores(df: pd.DataFrame, load_date: date) -> pd.DataFrame:
    out = pd.DataFrame()
    out['nomer']          = _safe_str(df.get('nomer', pd.Series(dtype=str)), 50)
    out['load_date']      = load_date
    out['full_name']      = _safe_str(df.get('full_name'))
    out['code_applicant'] = _safe_str(df.get('code_applicant'), 50)
    out['city']           = _safe_str(df.get('city'), 100)
    out['specialization'] = _safe_str(df.get('specialization'))
    out['program']        = _safe_str(df.get('program'))
    out['priority']       = _safe_int(df.get('priority', pd.Series(dtype=str)))
    out['score_without_vi'] = _safe_int(df.get('score_without_vi', pd.Series(dtype=str)))
    out['all_vi_passed']  = _safe_bool(df.get('all_vi_passed', pd.Series(dtype=str)))

    for r in ['rank1','rank2','rank3','rank4','rank5','rank6',
              'rank7','rank8','rank9','rank10','rank11','rank12','rank13']:
        out[r] = _safe_decimal(df.get(r, pd.Series(dtype=str)))

    out = out.dropna(subset=['nomer'])
    return out.drop_duplicates(subset=['nomer'])

def transform_contracts(df: pd.DataFrame, load_date: date) -> pd.DataFrame:
    out = pd.DataFrame()
    out['dogovor']          = _safe_str(df.get('dogovor', pd.Series(dtype=str)), 50)
    out['contract_date']    = df.get('contract_date', pd.Series(dtype=str)).apply(_parse_contract_date)
    out['load_date']        = load_date
    out['full_name']        = _safe_str(df.get('full_name'))
    out['code_applicant']   = _safe_str(df.get('code_applicant'), 50)
    out['uniq_code']        = _safe_str(df.get('uniq_code'))
    out['city']             = _safe_str(df.get('city'), 100)
    out['specialization']   = _safe_str(df.get('specialization'))
    out['program']          = _safe_str(df.get('program'))
    out['id_application']   = _normalize_id_application(df.get('id_application', pd.Series(dtype=str)))
    out['priority']         = _safe_int(df.get('priority', pd.Series(dtype=str)))
    out['admission_plan']   = _safe_str(df.get('admission_plan'), 100)
    out['payment_status']   = _normalize_payment_status(df.get('payment_status', pd.Series(dtype=str)))
    out['name_parent']      = _safe_str(df.get('name_parent'))
    out['number_parent']    = _safe_str(df.get('number_parent'), 50)
    out['bvi']              = _safe_str(df.get('bvi'), 50)
    out['ege']              = _safe_int(df.get('ege', pd.Series(dtype=str)))
    out['individual_achievements'] = _safe_int(df.get('individual_achievements', pd.Series(dtype=str)))
    out['total']            = _safe_decimal(df.get('total', pd.Series(dtype=str)))

    out = out.dropna(subset=['dogovor'])
    return out.drop_duplicates(subset=['dogovor'])

def transform_criteria(df: pd.DataFrame, load_date: date) -> pd.DataFrame:
    out = pd.DataFrame()
    out['scep']          = _safe_str(df.get('scep', pd.Series(dtype=str)), 50)
    out['load_date']     = load_date
    out['direction']     = _safe_str(df.get('direction'))
    out['program_name']  = _safe_str(df.get('program_name'))
    out['criteria_value']= _safe_str(df.get('criteria_value'))

    out = out.dropna(subset=['scep'])
    return out.drop_duplicates(subset=['scep'])
