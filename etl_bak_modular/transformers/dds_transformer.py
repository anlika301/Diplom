
import difflib
import pandas as pd
from datetime import date

def _fuzzy_canonicalize(series: pd.Series, cutoff: float = 0.88) -> pd.Series:
    freq = series.dropna().value_counts()
    canonical = list(freq.index)

    cache = {}
    def _match(v):
        if pd.isna(v):
            return v
        if v in cache:
            return cache[v]
        if v in freq:
            others = [c for c in canonical if c != v]
            matches = difflib.get_close_matches(v, others, n=1, cutoff=cutoff)
            result = matches[0] if matches and freq[matches[0]] > freq.get(v, 0) else v
        else:
            matches = difflib.get_close_matches(v, canonical, n=1, cutoff=cutoff)
            result = matches[0] if matches else v
        cache[v] = result
        return result

    return series.apply(_match)

def build_dim_applicants(
    ods_apps: pd.DataFrame,
    ods_scores: pd.DataFrame,
    ods_contracts: pd.DataFrame,
) -> pd.DataFrame:
    frames = []
    if not ods_apps.empty:
        frames.append(ods_apps[['code_applicant', 'full_name', 'city', 'uniq_code']].copy())
    if not ods_scores.empty:
        tmp = ods_scores[['code_applicant', 'full_name', 'city']].copy()
        tmp['uniq_code'] = None
        frames.append(tmp)
    if not ods_contracts.empty:
        frames.append(ods_contracts[['code_applicant', 'full_name', 'city', 'uniq_code']].copy())

    if not frames:
        return pd.DataFrame(columns=['code_applicant', 'full_name', 'city', 'uniq_code'])

    combined = pd.concat(frames, ignore_index=True)
    combined = combined.dropna(subset=['code_applicant'])
    combined = combined.drop_duplicates(subset=['code_applicant'], keep='last')
    return combined.reset_index(drop=True)

def normalize_program_fields(
    ods_apps: pd.DataFrame,
    ods_scores: pd.DataFrame,
    ods_contracts: pd.DataFrame,
) -> None:
    all_programs = pd.concat(
        [df['program'] for df in [ods_apps, ods_scores, ods_contracts] if not df.empty and 'program' in df.columns],
        ignore_index=True,
    )
    all_specs = pd.concat(
        [df['specialization'] for df in [ods_apps, ods_scores, ods_contracts] if not df.empty and 'specialization' in df.columns],
        ignore_index=True,
    )

    prog_map = dict(zip(all_programs, _fuzzy_canonicalize(all_programs)))
    spec_map = dict(zip(all_specs, _fuzzy_canonicalize(all_specs)))

    for df in [ods_apps, ods_scores, ods_contracts]:
        if not df.empty:
            if 'program' in df.columns:
                df['program'] = df['program'].map(prog_map).fillna(df['program'])
            if 'specialization' in df.columns:
                df['specialization'] = df['specialization'].map(spec_map).fillna(df['specialization'])

def build_dim_programs(
    ods_apps: pd.DataFrame,
    ods_scores: pd.DataFrame,
    ods_contracts: pd.DataFrame,
) -> pd.DataFrame:
    cols = ['program', 'specialization', 'city']
    frames = []
    for df in [ods_apps, ods_scores, ods_contracts]:
        if not df.empty:
            avail = [c for c in cols if c in df.columns]
            frames.append(df[avail].copy())

    if not frames:
        return pd.DataFrame(columns=cols)

    combined = pd.concat(frames, ignore_index=True)
    combined = combined.dropna(subset=['program'])
    combined = combined.drop_duplicates(subset=['program', 'specialization', 'city'])
    return combined.reset_index(drop=True)

def build_dim_criteria(ods_criteria: pd.DataFrame) -> pd.DataFrame:
    if ods_criteria.empty:
        return pd.DataFrame()
    return ods_criteria[['scep', 'direction', 'program_name', 'criteria_value']].copy()

def _make_applicant_map(dim_applicants: pd.DataFrame) -> dict:
    return dict(zip(dim_applicants['code_applicant'], dim_applicants['applicant_id']))

def _make_program_map(dim_programs: pd.DataFrame) -> dict:
    return dict(zip(
        zip(dim_programs['program'],
            dim_programs['specialization'],
            dim_programs['city']),
        dim_programs['program_id']
    ))

def build_fact_applications(
    ods_apps: pd.DataFrame,
    dim_applicants: pd.DataFrame,
    dim_programs: pd.DataFrame,
    load_date: date,
) -> pd.DataFrame:
    app_map = _make_applicant_map(dim_applicants)
    prg_map = _make_program_map(dim_programs)

    out = ods_apps.copy()
    out['applicant_id'] = out['code_applicant'].map(app_map)
    out['program_id']   = out.apply(
        lambda r: prg_map.get((r.get('program'), r.get('specialization'), r.get('city'))),
        axis=1
    )
    out['valid_from'] = load_date
    out['valid_to']   = None
    out['is_current'] = True

    out = out.rename(columns={'app_id': 'app_id'})

    cols = ['app_id', 'applicant_id', 'program_id', 'valid_from', 'valid_to', 'is_current',
            'priority', 'reg_number', 'uniq_code', 'sspvo_status']
    return out[[c for c in cols if c in out.columns]].dropna(subset=['applicant_id', 'program_id'])

def build_fact_scores(
    ods_scores: pd.DataFrame,
    dim_applicants: pd.DataFrame,
    dim_programs: pd.DataFrame,
    load_date: date,
) -> pd.DataFrame:
    app_map = _make_applicant_map(dim_applicants)
    prg_map = _make_program_map(dim_programs)

    out = ods_scores.copy()
    out['applicant_id'] = out['code_applicant'].map(app_map)
    out['program_id']   = out.apply(
        lambda r: prg_map.get((r.get('program'), r.get('specialization'), r.get('city'))),
        axis=1
    )
    out['valid_from'] = load_date
    out['valid_to']   = None
    out['is_current'] = True

    rank_cols = [f'rank{i}' for i in range(1, 14)]
    cols = (['nomer', 'applicant_id', 'program_id', 'valid_from', 'valid_to', 'is_current',
             'priority', 'score_without_vi', 'all_vi_passed'] + rank_cols)
    return out[[c for c in cols if c in out.columns]].dropna(subset=['applicant_id', 'program_id'])

def build_fact_contracts(
    ods_contracts: pd.DataFrame,
    dim_applicants: pd.DataFrame,
    dim_programs: pd.DataFrame,
    load_date: date,
) -> pd.DataFrame:
    app_map = _make_applicant_map(dim_applicants)
    prg_map = _make_program_map(dim_programs)

    out = ods_contracts.copy()
    out['applicant_id'] = out['code_applicant'].map(app_map)
    out['program_id']   = out.apply(
        lambda r: prg_map.get((r.get('program'), r.get('specialization'), r.get('city'))),
        axis=1
    )
    out['valid_from'] = load_date
    out['valid_to']   = None
    out['is_current'] = True

    cols = ['dogovor', 'contract_date', 'applicant_id', 'program_id', 'valid_from', 'valid_to', 'is_current',
            'id_application', 'priority', 'admission_plan', 'payment_status',
            'name_parent', 'number_parent', 'bvi', 'ege', 'individual_achievements',
            'total', 'uniq_code']
    return out[[c for c in cols if c in out.columns]].dropna(subset=['applicant_id', 'program_id'])

def classify_scd2_changes(
    new_df: pd.DataFrame,
    current_dds: pd.DataFrame,
    nat_key: str,
    compare_cols: list[str],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if current_dds.empty:
        return new_df, pd.DataFrame()

    merged = new_df.merge(
        current_dds[[nat_key] + compare_cols].add_suffix('_old'),
        left_on=nat_key, right_on=f'{nat_key}_old',
        how='left'
    )

    is_new = merged[f'{nat_key}_old'].isna()

    is_changed = pd.Series(False, index=merged.index)
    for c in compare_cols:
        both_null = merged[c].isna() & merged[f'{c}_old'].isna()
        differ    = merged[c].ne(merged[f'{c}_old']) & ~both_null
        is_changed = is_changed | differ

    to_insert_idx = is_new | is_changed
    to_insert = new_df[to_insert_idx.values].copy()

    changed_nks = new_df.loc[is_changed.values, nat_key].tolist()
    pk_col = [c for c in current_dds.columns if c.endswith('_dds_id')][0] if any(
        c.endswith('_dds_id') for c in current_dds.columns
    ) else None

    to_close = pd.DataFrame()
    if pk_col and changed_nks:
        to_close = current_dds[current_dds[nat_key].isin(changed_nks)][[pk_col, nat_key]]

    return to_insert, to_close
