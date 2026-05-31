
import os
from datetime import date
import logging
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine

PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / ".env.mag")

DB_HOST = os.getenv("DB_HOST")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

DATA_DIR = PROJECT_ROOT / "mag"
CSV_FILES = {
    "contracts": DATA_DIR / "dogovor_rows.csv",
    "payment_schedules": DATA_DIR / "grafics_rows.csv",
    "payments": DATA_DIR / "kvitancii_rows.csv",
    "criteria": DATA_DIR / "crit_mag_rows.csv",
    "admission_plan": DATA_DIR / "plan_rows.csv",
}

COLUMN_RENAMES_CONTRACTS = {
    "Есть файлы": "has_files",
    "Активен": "is_active",
    "Индекс способа заключения договор": "contract_index",
    "Есть ошибки заполнения": "has_errors",
    "Код": "contract_code",
    "Регистрационный номер": "applicant_code",
    "Статус оплаты": "payment_status",
    "Абитуриент": "applicant_name",
    "Дата заключения": "contract_date",
    "Источник": "source",
    "Филиал": "city",
    "Конкурсная группа": "specialization",
    "Факультет": "faculty",
    "Образовательная программа": "program_name",
    "Заявление": "application_text",
    "Заявка": "submission_type",
    "Вид оплаты": "payment_method",
    "Количество сторон": "party_count",
    "Тип заказчика": "customer_type",
    "Статус ИП": "ip_status",
    "Дата начала": "start_date",
    "Дата окончания": "end_date",
    "Комментарий": "comments",
    "Ответственный": "responsible",
    "Процент скидки (первый семестр)": "discount_percent",
    "Ссылка": "link",
    "Стоимость первого семестра (с учет": "semester_cost",
    "Сумма": "total_sum",
    "ФИО заказчика": "customer_name",
    "E-mail (физ. лицо)": "customer_email",
    "Email": "email",
}

COLUMN_RENAMES_PAYMENT_SCHEDULES = {
    "Код": "schedule_code",
    "Владелец": "owner",
    "Стоимость первого семестра (с учет": "semester_cost",
    "Абитуриент": "applicant_name",
    "Регистрационный номер": "applicant_code",
    "Скидка": "discount_text",
    "Значение скидки": "discount_value",
    "Статус оплаты": "payment_status",
    "Рег. номер": "reg_number",
    "Процент скидки (первый семестр)": "discount_percent",
}

COLUMN_RENAMES_PAYMENTS = {
    "Номер": "payment_id",
    "Пометка удаления": "deletion_mark",
    "Дата": "payment_date_upload",
    "Сумма": "payment_amount",
    "Договор": "contract_code_ref",
    "Наименование для печати": "payment_name",
    "Специальность": "specialization_payment",
    "Регистрационный номер": "applicant_code",
    "Есть обеспечительный платеж": "has_security_payment",
    "Абитуриент": "applicant_name",
    "Дата платежа": "payment_date",
    "Комментарий": "payment_comments",
    "Тип оплаты": "payment_type",
    "Ответственный": "payment_responsible",
}

COLUMN_RENAMES_CRITERIA = {
    "Программа": "program_name",
    "Критерий": "criteria_id",
}

COLUMN_RENAMES_ADMISSION_PLAN = {
    "Образовательная программа": "program_name",
    "Бюджетные места": "budget_seats",
    "по договорам": "contract_seats",
}

def get_engine():
    connection_string = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    return create_engine(connection_string, echo=False)

def setup_logging(log_dir=None):
    log_format = "%(asctime)s | %(levelname)-8s | %(message)s"
    logger = logging.getLogger("etl_mag")
    logger.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(log_format))
    logger.addHandler(console_handler)

    if log_dir:
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"etl_mag_{date.today()}.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(log_format))
        logger.addHandler(file_handler)

    return logger

today = date.today()
BATCH_SIZE = 5000
LOCK_TIMEOUT = "15s"

SCHEMAS = {
    "stg": "stg_mag",
    "ods": "ods_mag",
    "dds": "dds_mag",
    "mart": "mart_mag",
}

TABLE_NAMES = {
    "stg_contracts": "stg_mag.contracts",
    "stg_payment_schedules": "stg_mag.payment_schedules",
    "stg_payments": "stg_mag.payments",
    "stg_criteria": "stg_mag.criteria",
    "stg_admission_plan": "stg_mag.admission_plan",

    "ods_contracts": "ods_mag.contracts",
    "ods_payment_schedules": "ods_mag.payment_schedules",
    "ods_payments": "ods_mag.payments",
    "ods_criteria": "ods_mag.criteria",
    "ods_admission_plan": "ods_mag.admission_plan",

    "dds_dim_applicants": "dds_mag.dim_applicants",
    "dds_dim_programs": "dds_mag.dim_programs",
    "dds_dim_criteria": "dds_mag.dim_criteria",
    "dds_dim_admission_plans": "dds_mag.dim_admission_plans",

    "dds_fact_contracts": "dds_mag.fact_contracts",
    "dds_fact_payment_schedules": "dds_mag.fact_payment_schedules",
    "dds_fact_payments": "dds_mag.fact_payments",
}
