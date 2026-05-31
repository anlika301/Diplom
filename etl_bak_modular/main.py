

import sys
import logging
import argparse
import time
from datetime import date
from pathlib import Path
from typing import Dict, Any

sys.path.insert(0, str(Path(__file__).parent))

from config import get_engine, today, setup_logging
from extractors import extract_stg_table, extract_ods_table, extract_dds_fact_current

import transformers.ods_transformer as ods_tr
import transformers.dds_transformer as dds_tr
import transformers.mart_transformer as mart_tr

from loaders import upsert_ods, upsert_dim, apply_scd2

log = logging.getLogger('etl_bak')

def run_ods(engine, raw: dict, load_date: date, dry_run: bool) -> dict:
    log.info("=== СЛОЙ ODS (Operational Data Store) ===")

    ods_apps      = ods_tr.transform_applications(raw['applications'], load_date)
    ods_scores    = ods_tr.transform_scores(raw['scores'],             load_date)
    ods_contracts = ods_tr.transform_contracts(raw['contracts'],        load_date)
    ods_criteria  = ods_tr.transform_criteria(raw['criteria'],          load_date)

    upsert_ods(engine, ods_apps,      'applications', 'app_id',  dry_run)
    upsert_ods(engine, ods_scores,    'scores',       'nomer',   dry_run)
    upsert_ods(engine, ods_contracts, 'contracts',    'dogovor', dry_run)
    upsert_ods(engine, ods_criteria,  'criteria',     'scep',    dry_run)

    log.info("=== ODS завершён ===")
    return {
        'applications': ods_apps,
        'scores':       ods_scores,
        'contracts':    ods_contracts,
        'criteria':     ods_criteria,
    }

def run_dds(engine, ods: dict, load_date: date, dry_run: bool):
    log.info("=== СЛОЙ DDS (Detailed Data Store) ===")

    ods_apps      = ods['applications']
    ods_scores    = ods['scores']
    ods_contracts = ods['contracts']
    ods_criteria  = ods['criteria']

    dds_tr.normalize_program_fields(ods_apps, ods_scores, ods_contracts)

    dim_app_df = dds_tr.build_dim_applicants(ods_apps, ods_scores, ods_contracts)
    log.info("dim_applicants: %d уникальных абитуриентов", len(dim_app_df))
    dim_applicants = upsert_dim(engine, dim_app_df, 'dim_applicants', ['code_applicant'], dry_run)

    dim_prg_df = dds_tr.build_dim_programs(ods_apps, ods_scores, ods_contracts)
    log.info("dim_programs: %d уникальных программ", len(dim_prg_df))
    dim_programs = upsert_dim(engine, dim_prg_df, 'dim_programs', ['program', 'specialization', 'city'], dry_run)

    dim_crit_df = dds_tr.build_dim_criteria(ods_criteria)
    if not dim_crit_df.empty:
        log.info("dim_criteria: %d критериев", len(dim_crit_df))
        if not dim_programs.empty and 'program_id' in dim_programs.columns:
            prg_map = (
                dim_programs.groupby('program')['program_id']
                .first()
                .to_dict()
            )
            ambiguous = (
                dim_programs.groupby('program')['program_id']
                .count()
                .loc[lambda s: s > 1]
            )
            if not ambiguous.empty:
                log.warning(
                    "dim_criteria: %d программ имеют одинаковое название в разных "
                    "городах/специализациях — program_id берётся первый: %s",
                    len(ambiguous), list(ambiguous.index)
                )
            dim_crit_df['program_id'] = dim_crit_df['program_name'].map(prg_map)
            dim_crit_df = dim_crit_df.dropna(subset=['program_id'])
            dim_crit_df['program_id'] = dim_crit_df['program_id'].astype(int)
        dim_crit_df = dim_crit_df.drop(columns=['program_name'], errors='ignore')
        upsert_dim(engine, dim_crit_df, 'dim_criteria', ['scep'], dry_run)

    if dry_run or dim_applicants.empty or dim_programs.empty:
        log.info("Факты: пропуск (dry-run или пустые справочники)")
        log.info("=== DDS завершён ===")
        return

    fact_apps = dds_tr.build_fact_applications(ods_apps, dim_applicants, dim_programs, load_date)
    cur_apps  = extract_dds_fact_current(engine, 'fact_applications')
    to_ins, to_close = dds_tr.classify_scd2_changes(
        fact_apps, cur_apps, 'app_id', ['sspvo_status', 'priority']
    )
    apply_scd2(engine, to_ins, to_close, 'fact_applications', 'application_dds_id', load_date, dry_run)

    fact_scores = dds_tr.build_fact_scores(ods_scores, dim_applicants, dim_programs, load_date)
    cur_scores  = extract_dds_fact_current(engine, 'fact_scores')
    to_ins, to_close = dds_tr.classify_scd2_changes(
        fact_scores, cur_scores, 'nomer', ['rank2', 'rank3', 'rank4', 'rank5', 'rank6']
    )
    apply_scd2(engine, to_ins, to_close, 'fact_scores', 'score_dds_id', load_date, dry_run)

    fact_contracts = dds_tr.build_fact_contracts(ods_contracts, dim_applicants, dim_programs, load_date)
    cur_contracts  = extract_dds_fact_current(engine, 'fact_contracts')
    to_ins, to_close = dds_tr.classify_scd2_changes(
        fact_contracts, cur_contracts, 'dogovor', ['payment_status', 'total']
    )
    apply_scd2(engine, to_ins, to_close, 'fact_contracts', 'contract_dds_id', load_date, dry_run)

    log.info("=== DDS завершён ===")

def run_etl_layer(layer: str = "ods", log_dir: str = None, run: bool = True) -> Dict[str, Any]:
    if layer not in ["ods", "dds", "mart", "all"]:
        raise ValueError(f"Invalid layer: {layer}. Must be one of: ods, dds, mart, all")

    start_time = time.time()
    setup_logging(log_dir=log_dir)
    dry_run    = not run
    load_date  = today()

    log.info(f"Starting ETL layer: {layer} (dry_run={dry_run})")

    engine = get_engine()
    ods    = None

    try:
        if layer in ("ods", "all"):
            raw = {
                'applications': extract_stg_table(engine, 'applications'),
                'scores':       extract_stg_table(engine, 'scores'),
                'contracts':    extract_stg_table(engine, 'contracts'),
                'criteria':     extract_stg_table(engine, 'criteria'),
            }
            ods = run_ods(engine, raw, load_date, dry_run)

        if layer in ("dds", "all"):
            if ods is None:
                ods = {
                    'applications': extract_ods_table(engine, 'applications'),
                    'scores':       extract_ods_table(engine, 'scores'),
                    'contracts':    extract_ods_table(engine, 'contracts'),
                    'criteria':     extract_ods_table(engine, 'criteria'),
                }
            run_dds(engine, ods, load_date, dry_run)

        if layer in ("mart", "all"):
            mart_tr.run_mart(engine, dry_run)

        duration = time.time() - start_time
        log.info(f"ETL layer {layer} completed in {duration:.2f}s")
        return {'layer': layer, 'status': 'success', 'duration_sec': duration}

    except Exception as e:
        duration = time.time() - start_time
        log.error(f"ETL layer {layer} failed after {duration:.2f}s: {e}", exc_info=True)
        return {'layer': layer, 'status': 'error', 'duration_sec': duration, 'error': str(e)}
    finally:
        engine.dispose()

def parse_args():
    parser = argparse.ArgumentParser(description='ETL Бакалавриат (ODS → DDS → MART)')
    parser.add_argument('--layer', choices=['ods', 'dds', 'mart', 'all'], default='all')
    parser.add_argument('--date', type=str, default=None, help='Дата загрузки YYYY-MM-DD')
    parser.add_argument('--run', action='store_true', help='Реальная запись (без --run = dry-run)')
    parser.add_argument('--log-dir', type=str, default=None, help='Папка для файла лога')
    return parser.parse_args()

def main():
    args = parse_args()
    setup_logging(log_dir=args.log_dir)

    dry_run   = not args.run
    load_date = date.fromisoformat(args.date) if args.date else today()

    log.info("=" * 55)
    log.info("ETL БАКАЛАВРИАТ | Дата: %s | %s", load_date,
             'РЕАЛЬНАЯ ЗАПИСЬ' if not dry_run else 'DRY-RUN')
    log.info("=" * 55)

    engine = get_engine()
    ods    = None

    if args.layer in ('ods', 'all'):
        raw = {
            'applications': extract_stg_table(engine, 'applications'),
            'scores':       extract_stg_table(engine, 'scores'),
            'contracts':    extract_stg_table(engine, 'contracts'),
            'criteria':     extract_stg_table(engine, 'criteria'),
        }
        ods = run_ods(engine, raw, load_date, dry_run)

    if args.layer in ('dds', 'all'):
        if ods is None:
            ods = {
                'applications': extract_ods_table(engine, 'applications'),
                'scores':       extract_ods_table(engine, 'scores'),
                'contracts':    extract_ods_table(engine, 'contracts'),
                'criteria':     extract_ods_table(engine, 'criteria'),
            }
        run_dds(engine, ods, load_date, dry_run)

    if args.layer in ('mart', 'all'):
        mart_tr.run_mart(engine, dry_run)

    log.info("=" * 55)
    log.info("ETL ЗАВЕРШЁН %s", '(dry-run — данные не записаны)' if dry_run else '✓')
    log.info("=" * 55)

if __name__ == '__main__':
    main()
