
import os
import platform
import logging
import logging.handlers
from pathlib import Path
from datetime import date
from urllib.parse import quote_plus
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

_base = Path(__file__).parent
load_dotenv(_base / '.env.bak') or load_dotenv(_base.parent / '.env.bak')

os.environ.pop('PGSSLMODE', None)
os.environ.pop('PGSSLROOTCERT', None)

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / 'bak'

CSV_FILES = {
    'applications': DATA_DIR / 'application_bak_rows.csv',
    'scores':       DATA_DIR / 'ball_bak_rows.csv',
    'contracts':    DATA_DIR / 'dogovor_bak_rows.csv',
    'criteria':     DATA_DIR / 'kriterii_bak_rows.csv',
}

SCHEMAS = {
    'stg':  'stg_bak',
    'ods':  'ods_bak',
    'dds':  'dds_bak',
    'mart': 'mart_bak',
}

COLUMN_RENAMES = {
    'applications': {
        'Статус ССПВО':              'sspvo_status',
        'Уникальный код поступающего': 'uniq_code',
        'Регистрационный номер':     'reg_number',
        'Статус_ССПВО':              'sspvo_status',
        'Уникальный_код_поступающего': 'uniq_code',
        'Регистрационный_номер':     'reg_number',
    },
    'scores': {
        'Номер':          'nomer',
        'progpam':        'program',
        'Без ВИ':         'score_without_vi',
        'Без_ВИ':         'score_without_vi',
        'Все ВИ пройдены': 'all_vi_passed',
        'Все_ВИ_пройдены': 'all_vi_passed',
        'code':           'code_applicant',
        'Ранг5':          'rank5',
        'Ранг6':          'rank6',
        'Ранг7':          'rank7',
        'Ранг8':          'rank8',
        'Ранг9':          'rank9',
        'Ранг10':         'rank10',
        'Ранг11':         'rank11',
        'Ранг12':         'rank12',
        'Ранг13':         'rank13',
        'Ранг':           '_drop',
    },
    'contracts': {
        'Уникальный код поступающего': 'uniq_code',
        'Уникальный_код_поступающего': 'uniq_code',
        'BVI':                         'bvi',
        'EGE':                         'ege',
        'Individual_achievements':     'individual_achievements',
        'id':                          'id_application',
    },
    'criteria': {
        'сцеп':                    'scep',
        'Направление подготовки':  'direction',
        'Направление_подготовки':  'direction',
        'Образовательная программа': 'program_name',
        'Образовательная_программа': 'program_name',
        'Критерий':                'criteria_value',
    },
}

def setup_logging(log_dir: Path = None) -> None:
    fmt = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s', '%H:%M:%S')
    root = logging.getLogger('etl_bak')
    root.setLevel(logging.INFO)
    if root.handlers:
        return

    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    root.addHandler(sh)

    if log_dir:
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        fh = logging.handlers.RotatingFileHandler(
            log_dir / 'etl_bak.log', maxBytes=5_000_000, backupCount=3, encoding='utf-8'
        )
        fh.setFormatter(fmt)
        root.addHandler(fh)

def get_engine():
    host     = os.getenv('DB_HOST')
    port     = os.getenv('DB_PORT', '6543')
    name     = os.getenv('DB_NAME', 'postgres')
    user     = os.getenv('DB_USER')
    password = os.getenv('DB_PASSWORD')

    url = (
        f"postgresql+psycopg2://{quote_plus(user)}:{quote_plus(password)}"
        f"@{host}:{port}/{name}"
    )
    connect_args: dict = {
        'sslmode': 'require',
        'connect_timeout': 30,
        'application_name': 'etl_bak',
        'keepalives': 1,
        'keepalives_idle': 30,
        'keepalives_interval': 10,
        'keepalives_count': 5,
    }
    if platform.system() == 'Windows':
        connect_args['gssencmode'] = 'disable'

    return create_engine(
        url,
        pool_pre_ping=True,
        pool_recycle=300,
        connect_args=connect_args,
    )

def today() -> date:
    return date.today()
