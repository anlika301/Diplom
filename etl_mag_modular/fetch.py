
import sys
import logging
import argparse
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd

from config import (
    get_engine, today, setup_logging, TABLE_NAMES,
    COLUMN_RENAMES_CONTRACTS, COLUMN_RENAMES_PAYMENT_SCHEDULES,
    COLUMN_RENAMES_PAYMENTS, COLUMN_RENAMES_CRITERIA, COLUMN_RENAMES_ADMISSION_PLAN,
)
from transformers.stg_transformer import (
    transform_stg_contracts, transform_stg_payment_schedules,
    transform_stg_payments, transform_stg_criteria, transform_stg_admission_plan,
)
from loaders import append_to_stg

log = logging.getLogger('fetch_mag')

DEFAULT_FOLDER = r'\\fs5\ФАО центр фин обеспечения ДБ\Анжелика\MAG'

FILE_PATTERNS = {
    ('договор', 'dogovor'):         'contracts',
    ('граф', 'grafic'):             'payment_schedules',
    ('квитанц', 'kvitanc'):        'payments',
    ('крит', 'crit'):               'criteria',
    ('план', 'plan'):               'admission_plan',
}

STG_PKS = {
    'contracts':          'contract_code',
    'payment_schedules':  'schedule_code',
    'payments':           'payment_id',
    'criteria':           ('program_name', 'criteria_id'),
    'admission_plan':     'program_name',
}

STG_TABLE_KEYS = {
    'contracts':         'stg_contracts',
    'payment_schedules': 'stg_payment_schedules',
    'payments':          'stg_payments',
    'criteria':          'stg_criteria',
    'admission_plan':    'stg_admission_plan',
}

STG_TRANSFORMS = {
    'contracts':         transform_stg_contracts,
    'payment_schedules': transform_stg_payment_schedules,
    'payments':          transform_stg_payments,
    'criteria':          transform_stg_criteria,
    'admission_plan':    transform_stg_admission_plan,
}

PER_TABLE_RENAMES = {
    'contracts':         COLUMN_RENAMES_CONTRACTS,
    'payment_schedules': COLUMN_RENAMES_PAYMENT_SCHEDULES,
    'payments':          COLUMN_RENAMES_PAYMENTS,
    'criteria':          COLUMN_RENAMES_CRITERIA,
    'admission_plan':    COLUMN_RENAMES_ADMISSION_PLAN,
}

EXTENSIONS = ('*.xlsx', '*.xls', '*.csv')

def _read_file(path: Path, renames: dict) -> pd.DataFrame:
    log.info("Читаю файл: %s", path.name)
    ext = path.suffix.lower()
    if ext in ('.xlsx', '.xls'):
        df = pd.read_excel(path, sheet_name=0, engine='openpyxl')
    else:
        for enc in ('utf-8-sig', 'utf-8', 'cp1251'):
            try:
                df = pd.read_csv(path, encoding=enc, sep=None, engine='python')
                break
            except UnicodeDecodeError:
                continue
    df = df.rename(columns=renames)
    keep = set(renames.values())
    df = df[[c for c in df.columns if c in keep]]
    log.info("  → %d строк, %d колонок", len(df), len(df.columns))
    return df

def scan_folder(folder: Path) -> dict:
    all_files = []
    for pat in EXTENSIONS:
        all_files.extend(folder.glob(pat))

    found = {v: [] for v in STG_PKS}
    for f in all_files:
        name_lower = f.stem.lower()
        for prefixes, key in FILE_PATTERNS.items():
            if any(name_lower.startswith(p) for p in prefixes):
                found[key].append(f)
                break

    result = {}
    for key, candidates in found.items():
        if not candidates:
            log.warning("Файл для '%s' не найден в %s", key, folder)
            result[key] = None
        elif len(candidates) == 1:
            result[key] = candidates[0]
        else:
            latest = max(candidates, key=lambda p: p.stat().st_mtime)
            log.warning("Найдено %d файлов для '%s', беру самый новый: %s",
                        len(candidates), key, latest.name)
            result[key] = latest
    return result

def fetch_mag_stg(folder: str, run: bool = True, load_date: date = None) -> dict:
    setup_logging()
    dry_run   = not run
    load_date = load_date or date.today()
    folder_p  = Path(folder)

    log.info("FETCH MAG | Папка: %s | %s", folder_p, 'ЗАПИСЬ' if run else 'DRY-RUN')

    if not folder_p.exists():
        raise FileNotFoundError(f"Папка не найдена: {folder_p}")

    files  = scan_folder(folder_p)
    engine = get_engine()
    total  = 0

    for key in ('contracts', 'payment_schedules', 'payments', 'criteria', 'admission_plan'):
        path = files.get(key)
        if path is None:
            log.warning("STG %s: файл не найден, пропускаю", key)
            continue
        df_raw  = _read_file(path, PER_TABLE_RENAMES[key])
        df_stg  = STG_TRANSFORMS[key](df_raw)
        tbl_key = STG_TABLE_KEYS[key]
        if dry_run:
            n = len(df_stg)
            log.info("STG %s: %d строк [dry-run]", key, n)
        else:
            n = append_to_stg(engine, df_stg, TABLE_NAMES[tbl_key])
            log.info("STG %s: %d строк ✓", key, n)
        total += n

    log.info("FETCH MAG завершён: %d строк", total)
    return {'status': 'success', 'rows_loaded': total, 'pipeline': 'mag'}

def main():
    p = argparse.ArgumentParser(description='Загрузка MAG файлов из папки в STG')
    p.add_argument('--folder', default=DEFAULT_FOLDER)
    p.add_argument('--date', dest='load_date', default=None)
    p.add_argument('--run', action='store_true')
    args = p.parse_args()

    result = fetch_mag_stg(
        folder=args.folder,
        run=args.run,
        load_date=date.fromisoformat(args.load_date) if args.load_date else None,
    )
    print(result)

if __name__ == '__main__':
    main()
