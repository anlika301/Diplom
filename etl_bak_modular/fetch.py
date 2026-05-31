

import sys
import logging
import argparse
from datetime import date
from pathlib import Path

_this_dir = Path(__file__).parent
if (_this_dir / 'config.py').exists():
    sys.path.insert(0, str(_this_dir))
else:
    sys.path.insert(0, str(_this_dir / 'etl_bak_modular'))

import pandas as pd

from config import get_engine, today, setup_logging, COLUMN_RENAMES
import transformers.stg_transformer as stg_tr
from loaders import append_to_stg

log = logging.getLogger('etl_bak')

DEFAULT_FOLDER = ''

FILE_PATTERNS = {
    'заявлени':    'applications',
    'application': 'applications',
    'балл':        'scores',
    'ball':        'scores',
    'договор':     'contracts',
    'dogovor':     'contracts',
    'критери':     'criteria',
    'kriterii':    'criteria',
}

STG_PKS = {
    'applications': 'id',
    'scores':       'nomer',
    'contracts':    'dogovor',
    'criteria':     'scep',
}

STG_TRANSFORMS = {
    'applications': stg_tr.transform_applications,
    'scores':       stg_tr.transform_scores,
    'contracts':    stg_tr.transform_contracts,
    'criteria':     stg_tr.transform_criteria,
}

STG_KEEP_COLS = {
    'applications': ['id', 'city', 'full_name', 'code_applicant', 'priority',
                     'specialization', 'program', 'reg_number', 'uniq_code',
                     'sspvo_status', 'load_date', 'source_file'],
    'scores':       ['nomer', 'full_name', 'code_applicant', 'priority',
                     'specialization', 'program', 'city', 'score_without_vi',
                     'all_vi_passed', 'rank1', 'rank2', 'rank3', 'rank4',
                     'rank5', 'rank6', 'rank7', 'rank8', 'rank9', 'rank10',
                     'rank11', 'rank12', 'rank13', 'load_date', 'source_file'],
    'contracts':    ['dogovor', 'full_name', 'code_applicant', 'uniq_code',
                     'city', 'payment_status', 'name_parent', 'number_parent',
                     'specialization', 'id_application', 'program', 'priority',
                     'admission_plan', 'bvi', 'ege', 'individual_achievements',
                     'total', 'load_date', 'source_file'],
    'criteria':     ['scep', 'direction', 'program_name', 'criteria_value',
                     'load_date', 'source_file'],
}

EXTENSIONS = ('*.xlsx', '*.xls', '*.csv')

def _filter_stg(df: 'pd.DataFrame', key: str) -> 'pd.DataFrame':
    pk   = STG_PKS[key]
    keep = [c for c in STG_KEEP_COLS[key] if c in df.columns]
    missing = [c for c in STG_KEEP_COLS[key] if c not in df.columns]
    if missing:
        log.warning("STG %s: колонки отсутствуют в файле: %s", key, missing)
    df = df[keep]
    if pk in df.columns:
        before = len(df)
        df = df.dropna(subset=[pk])
        dropped = before - len(df)
        if dropped:
            log.warning("STG %s: пропущено %d строк с NULL PK (%s)", key, dropped, pk)
    else:
        log.warning("STG %s: PK-колонка '%s' не найдена — строки не фильтруются", key, pk)
    return df

def _read_csv_auto(path: Path) -> pd.DataFrame:
    for encoding in ('utf-8-sig', 'utf-8', 'cp1251', 'windows-1251'):
        try:
            df = pd.read_csv(path, encoding=encoding, sep=None,
                             engine='python')
            log.info("  → кодировка: %s, разделитель определён автоматически", encoding)
            return df
        except (UnicodeDecodeError, Exception):
            continue
    raise ValueError(f"Не удалось прочитать CSV: {path.name}")

def _read_file(path: Path, key: str) -> pd.DataFrame:
    log.info("Читаю файл: %s", path.name)

    ext = path.suffix.lower()
    if ext in ('.xlsx', '.xls'):
        df = pd.read_excel(path, sheet_name=0, engine='openpyxl')
    elif ext == '.csv':
        df = _read_csv_auto(path)
    else:
        raise ValueError(f"Неподдерживаемый формат: {ext}")

    log.info("  → %d строк, %d колонок", len(df), len(df.columns))

    renames = COLUMN_RENAMES.get(key, {})
    df = df.rename(columns=renames)

    drop_cols = [c for c in df.columns if c == '_drop']
    if drop_cols:
        df = df.drop(columns=drop_cols)

    if key == 'criteria':
        df = df.dropna(how='all')

    return df

def scan_folder(folder: Path) -> dict[str, list[Path]]:
    all_files = []
    for pattern in EXTENSIONS:
        all_files.extend(folder.glob(pattern))

    if not all_files:
        log.warning("В папке %s не найдено файлов (.xlsx, .xls, .csv)", folder)
        return {k: [] for k in FILE_PATTERNS.values()}

    found: dict[str, list[Path]] = {k: [] for k in FILE_PATTERNS.values()}
    for f in all_files:
        name_lower = f.stem.lower()
        for prefix, key in FILE_PATTERNS.items():
            if name_lower.startswith(prefix):
                found[key].append(f)
                break

    result: dict[str, list[Path]] = {}
    for key, candidates in found.items():
        if not candidates:
            log.warning("Файл для '%s' не найден в %s", key, folder)
            result[key] = []
        else:
            sorted_candidates = sorted(candidates, key=lambda p: p.stat().st_mtime)
            names = [p.name for p in sorted_candidates]
            log.info("Категория '%s': %d файл(ов) → %s", key, len(sorted_candidates), names)
            result[key] = sorted_candidates

    return result

def parse_args():
    p = argparse.ArgumentParser(description='Загрузка файлов из сетевой папки в STG')
    p.add_argument('--folder', default=DEFAULT_FOLDER,
                   help='Путь к папке с файлами')
    p.add_argument('--date', dest='load_date', default=None,
                   help='Дата загрузки YYYY-MM-DD (по умолчанию — сегодня)')
    p.add_argument('--run', action='store_true',
                   help='Реальная запись в БД (без --run = dry-run)')
    return p.parse_args()

def fetch_bak_stg(folder: str, run: bool = True, load_date: date = None) -> dict:
    setup_logging()
    dry_run   = not run
    load_date = load_date or today()
    folder_p  = Path(folder)

    log.info("FETCH BAK | Папка: %s | %s", folder_p,
             'ЗАПИСЬ' if run else 'DRY-RUN')

    if not folder_p.exists():
        raise FileNotFoundError(f"Папка не найдена: {folder_p}")

    files  = scan_folder(folder_p)
    engine = get_engine()
    total  = 0

    for key in ('applications', 'scores', 'contracts', 'criteria'):
        paths = files.get(key, [])
        if not paths:
            log.warning("STG %s: файл не найден, пропускаю", key)
            continue
        for path in paths:
            df_raw = _read_file(path, key)
            df_stg = _filter_stg(STG_TRANSFORMS[key](df_raw, load_date), key)
            n = append_to_stg(engine, df_stg, key, STG_PKS[key], dry_run)
            total += n
            log.info("STG %s (%s): %d строк %s", key, path.name, n,
                     '[dry-run]' if dry_run else '✓')

    log.info("FETCH BAK завершён: %d строк", total)
    return {'status': 'success', 'rows_loaded': total, 'pipeline': 'bak'}

def main():
    args = parse_args()
    setup_logging()

    dry_run   = not args.run
    load_date = date.fromisoformat(args.load_date) if args.load_date else today()
    folder    = Path(args.folder)

    log.info("=" * 55)
    log.info("FETCH FROM NETWORK | Дата: %s | %s", load_date,
             'РЕАЛЬНАЯ ЗАПИСЬ' if not dry_run else 'DRY-RUN')
    log.info("Папка: %s", folder)
    log.info("=" * 55)

    if not folder.exists():
        log.error("Папка не найдена: %s", folder)
        log.error("Проверьте, что сетевой диск подключён и путь корректен.")
        sys.exit(1)

    files = scan_folder(folder)
    engine = get_engine()
    total_loaded = 0

    for key in ('applications', 'scores', 'contracts', 'criteria'):
        paths = files.get(key, [])
        if not paths:
            log.warning("STG %s: файл не найден, пропускаю", key)
            continue
        for path in paths:
            try:
                df_raw = _read_file(path, key)
                df_stg = _filter_stg(STG_TRANSFORMS[key](df_raw, load_date), key)
                n = append_to_stg(engine, df_stg, key, STG_PKS[key], dry_run)
                total_loaded += n
                log.info("STG %s (%s): %d строк %s", key, path.name, n,
                         '[dry-run]' if dry_run else '✓')
            except Exception:
                log.exception("Ошибка при загрузке %s (%s)", key, path.name)

    log.info("=" * 55)
    log.info("ЗАВЕРШЕНО: %d строк %s", total_loaded,
             '(dry-run — данные не записаны)' if dry_run else 'загружено в STG')
    log.info("=" * 55)

if __name__ == '__main__':
    main()
