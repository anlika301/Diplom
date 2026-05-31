
import argparse
import logging
import time
from typing import Dict, Any

from config import get_engine, setup_logging, today, TABLE_NAMES
from loaders import upsert_ods, upsert_dim, apply_scd2

from extractors import (
    extract_ods_contracts, extract_ods_payment_schedules, extract_ods_payments,
    extract_ods_criteria, extract_ods_admission_plan,
    extract_dds_dim_applicants, extract_dds_dim_programs, extract_dds_fact_contracts_current
)

from transformers.ods_transformer import (
    transform_ods_contracts, transform_ods_payment_schedules,
    transform_ods_payments, transform_ods_criteria, transform_ods_admission_plan
)

from transformers.dds_transformer import (
    build_dim_applicants, build_dim_programs, build_dim_criteria,
    build_dim_admission_plans, build_fact_contracts,
    build_fact_payment_schedules, build_fact_payments
)

from transformers.mart_transformer import run_daily_stats, generate_excel

def run_ods(engine, logger, dry_run=False):
    logger.info("=" * 80)
    logger.info("LAYER ODS: Transform and deduplicate")
    logger.info("=" * 80)

    try:
        logger.info("Transforming contracts...")
        from loaders import read_staging_table
        df_stg = read_staging_table(engine, TABLE_NAMES["stg_contracts"])
        df_ods = transform_ods_contracts(df_stg)
        logger.info(f"  → {len(df_ods)} rows after dedup")
        if not dry_run:
            upsert_ods(engine, df_ods, TABLE_NAMES["ods_contracts"], 'code')
            logger.info(f"  ✓ Upserted to {TABLE_NAMES['ods_contracts']}")

        logger.info("Transforming payment schedules...")
        df_stg = read_staging_table(engine, TABLE_NAMES["stg_payment_schedules"])
        df_ods = transform_ods_payment_schedules(df_stg)
        logger.info(f"  → {len(df_ods)} rows after dedup")
        if not dry_run:
            upsert_ods(engine, df_ods, TABLE_NAMES["ods_payment_schedules"], 'schedule_code')
            logger.info(f"  ✓ Upserted to {TABLE_NAMES['ods_payment_schedules']}")

        logger.info("Transforming payments...")
        df_stg = read_staging_table(engine, TABLE_NAMES["stg_payments"])
        df_ods = transform_ods_payments(df_stg)
        logger.info(f"  → {len(df_ods)} rows after dedup")
        if not dry_run:
            upsert_ods(engine, df_ods, TABLE_NAMES["ods_payments"], 'payment_id')
            logger.info(f"  ✓ Upserted to {TABLE_NAMES['ods_payments']}")

        logger.info("Transforming criteria...")
        df_stg = read_staging_table(engine, TABLE_NAMES["stg_criteria"])
        df_ods = transform_ods_criteria(df_stg)
        logger.info(f"  → {len(df_ods)} rows after dedup")
        if not dry_run:
            upsert_ods(engine, df_ods, TABLE_NAMES["ods_criteria"], ['program_name', 'criteria_id'])
            logger.info(f"  ✓ Upserted to {TABLE_NAMES['ods_criteria']}")

        logger.info("Transforming admission plan...")
        df_stg = read_staging_table(engine, TABLE_NAMES["stg_admission_plan"])
        df_ods = transform_ods_admission_plan(df_stg)
        logger.info(f"  → {len(df_ods)} rows after dedup")
        if not dry_run:
            upsert_ods(engine, df_ods, TABLE_NAMES["ods_admission_plan"], 'program_name')
            logger.info(f"  ✓ Upserted to {TABLE_NAMES['ods_admission_plan']}")

        logger.info("✓ ODS layer complete")
        return True

    except Exception as e:
        logger.error(f"✗ ODS layer failed: {e}", exc_info=True)
        return False

def run_dds(engine, logger, dry_run=False):
    logger.info("=" * 80)
    logger.info("LAYER DDS: Build normalized schema with history")
    logger.info("=" * 80)

    try:
        logger.info("Extracting ODS data...")
        ods_contracts = extract_ods_contracts(engine)
        ods_schedules = extract_ods_payment_schedules(engine)
        ods_criteria = extract_ods_criteria(engine)
        ods_plan = extract_ods_admission_plan(engine)
        logger.info(f"  ✓ Extracted {len(ods_contracts)} contracts, {len(ods_schedules)} schedules")

        logger.info("Building dimensions...")
        dim_applicants = build_dim_applicants(ods_contracts)
        dim_programs = build_dim_programs(ods_contracts, ods_criteria, ods_plan)
        dim_admission_plans = build_dim_admission_plans(ods_plan, dim_programs)
        dim_criteria = build_dim_criteria(ods_criteria, dim_admission_plans)
        logger.info(f"  ✓ Built {len(dim_applicants)} applicants, {len(dim_programs)} programs")

        if not dry_run:
            upsert_dim(engine, dim_applicants, TABLE_NAMES["dds_dim_applicants"], ['applicant_code'])
            upsert_dim(engine, dim_programs, TABLE_NAMES["dds_dim_programs"], ['program_name'])
            upsert_dim(engine, dim_admission_plans, TABLE_NAMES["dds_dim_admission_plans"], ['program_name'])
            upsert_dim(engine, dim_criteria, TABLE_NAMES["dds_dim_criteria"], ['program_name', 'criteria_id'])
            logger.info("  ✓ Loaded dimensions to DDS")

        logger.info("Building facts...")
        fact_contracts = build_fact_contracts(ods_contracts, dim_applicants, dim_programs)
        fact_schedules = build_fact_payment_schedules(ods_schedules, dim_applicants)
        fact_payments = build_fact_payments(extract_ods_payments(engine), dim_applicants)
        logger.info(f"  ✓ Built {len(fact_contracts)} contract facts, {len(fact_schedules)} schedule facts")

        if not dry_run:
            apply_scd2(
                engine, TABLE_NAMES["dds_fact_contracts"], fact_contracts,
                tracked_fields=['payment_status', 'discount_percent', 'semester_cost'],
                pk_col='ods_contract_code'
            )
            logger.info("  ✓ Loaded contracts facts with SCD2")

            apply_scd2(
                engine, TABLE_NAMES["dds_fact_payment_schedules"], fact_schedules,
                tracked_fields=['discount_value', 'payment_status'],
                pk_col='schedule_code'
            )
            logger.info("  ✓ Loaded payment schedule facts with SCD2")

            apply_scd2(
                engine, TABLE_NAMES["dds_fact_payments"], fact_payments,
                tracked_fields=['payment_amount'],
                pk_col='payment_id'
            )
            logger.info("  ✓ Loaded payment facts with SCD2")

        logger.info("✓ DDS layer complete")
        return True

    except Exception as e:
        logger.error(f"✗ DDS layer failed: {e}", exc_info=True)
        return False

def run_mart(engine, logger, dry_run=False, excel=False):
    logger.info("=" * 80)
    logger.info("LAYER MART: Daily stats report")
    logger.info("=" * 80)

    try:
        today_str = today.strftime("%Y_%m_%d")

        count = run_daily_stats(engine, today_str, dry_run=dry_run)
        if not dry_run:
            logger.info(f"  ✓ Создана таблица stats_{today_str} ({count} строк)")

        if excel and not dry_run:
            filename = generate_excel(engine, today_str)
            logger.info(f"  ✓ Excel: {filename}")

        logger.info("✓ MART layer complete")
        return True

    except Exception as e:
        logger.error(f"✗ MART layer failed: {e}", exc_info=True)
        return False

def run_etl_layer(layer: str = "ods", log_dir: str = None, run: bool = True) -> Dict[str, Any]:
    if layer not in ["ods", "dds", "mart", "all"]:
        raise ValueError(f"Invalid layer: {layer}. Must be one of: ods, dds, mart, all")

    start_time = time.time()
    engine = get_engine()
    logger = setup_logging(log_dir)

    logger.info(f"Starting ETL layer: {layer} (dry_run={not run})")

    success = True
    rows_processed = 0

    try:
        dry_run = not run

        if layer in ["ods", "all"] and success:
            result = run_ods(engine, logger, dry_run=dry_run)
            if not result:
                success = False
                raise Exception("ODS layer failed")

        if layer in ["dds", "all"] and success:
            result = run_dds(engine, logger, dry_run=dry_run)
            if not result:
                success = False
                raise Exception("DDS layer failed")

        if layer in ["mart", "all"] and success:
            result = run_mart(engine, logger, dry_run=dry_run, excel=False)
            if not result:
                success = False
                raise Exception("MART layer failed")

        duration = time.time() - start_time
        logger.info(f"✓ ETL layer {layer} completed in {duration:.2f}s")

        return {
            'layer': layer,
            'status': 'success',
            'duration_sec': duration,
            'rows_processed': 0,
        }

    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"✗ ETL layer {layer} failed after {duration:.2f}s: {e}", exc_info=True)

        return {
            'layer': layer,
            'status': 'error',
            'duration_sec': duration,
            'rows_processed': 0,
            'error': str(e),
        }
    finally:
        engine.dispose()

def main():
    parser = argparse.ArgumentParser(description="MAG ETL Pipeline")
    parser.add_argument("--layer", choices=["ods", "dds", "mart", "all"], default="all",
                       help="Which layer to run")
    parser.add_argument("--run", action="store_true", help="Actually write to DB (else dry-run)")
    parser.add_argument("--excel", action="store_true", help="Generate Excel file after MART")
    parser.add_argument("--log-dir", help="Directory for log files")

    args = parser.parse_args()

    engine = get_engine()
    logger = setup_logging(args.log_dir)

    logger.info(f"ETL Pipeline MAG - {today}")
    logger.info(f"Mode: {'LOAD' if args.run else 'DRY-RUN'}")
    logger.info("")

    success = True

    if args.layer in ["ods", "all"] and success:
        if not run_ods(engine, logger, dry_run=not args.run):
            success = False

    if args.layer in ["dds", "all"] and success:
        if not run_dds(engine, logger, dry_run=not args.run):
            success = False

    if args.layer in ["mart", "all"] and success:
        if not run_mart(engine, logger, dry_run=not args.run, excel=args.excel):
            success = False

    logger.info("")
    if success:
        logger.info("✓ ETL Pipeline Complete")
    else:
        logger.error("✗ ETL Pipeline Failed")

    return 0 if success else 1

if __name__ == "__main__":
    exit(main())
