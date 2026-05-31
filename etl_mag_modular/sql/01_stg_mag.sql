

CREATE SCHEMA IF NOT EXISTS stg_mag;


CREATE TABLE IF NOT EXISTS stg_mag.contracts (
  contract_code        TEXT PRIMARY KEY,
  has_files            TEXT,
  is_active            TEXT,
  contract_index       TEXT,
  has_errors           TEXT,
  applicant_code       TEXT,
  payment_status       TEXT,
  applicant_name       TEXT,
  contract_date        TEXT,
  source               TEXT,
  city                 TEXT,
  specialization       TEXT,
  faculty              TEXT,
  program_name         TEXT,
  application_text     TEXT,
  submission_type      TEXT,
  payment_method       TEXT,
  party_count          TEXT,
  customer_type        TEXT,
  ip_status            TEXT,
  start_date           TEXT,
  end_date             TEXT,
  comments             TEXT,
  responsible          TEXT,
  discount_percent     TEXT,
  link                 TEXT,
  semester_cost        TEXT,
  total_sum            TEXT,
  customer_name        TEXT,
  customer_email       TEXT,
  email                TEXT,
  load_date            DATE,
  source_file          TEXT
);

CREATE TABLE IF NOT EXISTS stg_mag.payment_schedules (
  schedule_code        TEXT PRIMARY KEY,
  owner                TEXT,
  semester_cost        TEXT,
  applicant_name       TEXT,
  applicant_code       TEXT,
  discount_text        TEXT,
  discount_value       TEXT,
  payment_status       TEXT,
  reg_number           TEXT,
  discount_percent     TEXT,
  load_date            DATE,
  source_file          TEXT
);

CREATE TABLE IF NOT EXISTS stg_mag.payments (
  payment_id            TEXT PRIMARY KEY,
  deletion_mark         TEXT,
  payment_date_upload   TEXT,
  payment_amount        TEXT,
  contract_code_ref     TEXT,
  payment_name          TEXT,
  specialization_payment TEXT,
  applicant_code        TEXT,
  has_security_payment  TEXT,
  applicant_name        TEXT,
  payment_date          TEXT,
  payment_comments      TEXT,
  payment_type          TEXT,
  payment_responsible   TEXT,
  load_date             DATE,
  source_file           TEXT
);


CREATE TABLE IF NOT EXISTS stg_mag.criteria (
  program_name   TEXT,
  criteria_id    TEXT,
  load_date      DATE,
  source_file    TEXT,
  PRIMARY KEY (program_name, criteria_id)
);

CREATE TABLE IF NOT EXISTS stg_mag.admission_plan (
  program_name    TEXT PRIMARY KEY,
  budget_seats    TEXT,
  contract_seats  TEXT,
  load_date       DATE,
  source_file     TEXT
);

CREATE INDEX IF NOT EXISTS idx_stg_contracts_applicant ON stg_mag.contracts(applicant_code);
CREATE INDEX IF NOT EXISTS idx_stg_contracts_program   ON stg_mag.contracts(program_name);
CREATE INDEX IF NOT EXISTS idx_stg_payments_contract   ON stg_mag.payments(contract_code_ref);
CREATE INDEX IF NOT EXISTS idx_stg_schedules_applicant ON stg_mag.payment_schedules(applicant_code);
