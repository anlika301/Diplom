
CREATE SCHEMA IF NOT EXISTS ods_mag;

CREATE TABLE IF NOT EXISTS ods_mag.contracts (
  code              VARCHAR PRIMARY KEY,
  has_files         BOOLEAN,
  is_active         INTEGER,
  contract_code     TEXT,
  applicant_code    VARCHAR,
  payment_status    TEXT,
  applicant_name    TEXT,
  contract_date     DATE,
  source            TEXT,
  city              TEXT,
  specialization    TEXT,
  faculty           TEXT,
  program_name      TEXT,
  application_id    VARCHAR,
  application_text  TEXT,
  contract_index    TEXT,
  has_errors        BOOLEAN,
  submission_type   TEXT,
  payment_method    TEXT,
  party_count       INTEGER,
  customer_type     TEXT,
  ip_status         TEXT,
  start_date        DATE,
  end_date          DATE,
  comments          TEXT,
  responsible       TEXT,
  discount_percent  DECIMAL,
  link              TEXT,
  semester_cost     DECIMAL,
  total_sum         DECIMAL,
  customer_name     TEXT,
  customer_email    TEXT,
  email             TEXT,
  updated_at        TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ods_mag.payment_schedules (
  schedule_code    VARCHAR PRIMARY KEY,
  owner            TEXT,
  semester_cost    DECIMAL,
  applicant_name   TEXT,
  applicant_code   VARCHAR,
  discount_text    TEXT,
  discount_value   DECIMAL,
  payment_status   TEXT,
  reg_number       VARCHAR,
  discount_percent DECIMAL,
  updated_at       TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ods_mag.payments (
  payment_id            INTEGER PRIMARY KEY,
  deletion_mark         BOOLEAN,
  payment_date_upload   DATE,
  payment_amount        DECIMAL,
  contract_code         VARCHAR,
  payment_name          TEXT,
  specialization        TEXT,
  applicant_code        VARCHAR,
  has_security_payment  BOOLEAN,
  applicant_name        TEXT,
  payment_date          DATE,
  comments              TEXT,
  payment_type          TEXT,
  responsible           TEXT,
  updated_at            TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ods_mag.criteria (
  program_name  TEXT,
  criteria_id   INTEGER,
  updated_at    TIMESTAMPTZ DEFAULT NOW(),
  PRIMARY KEY (program_name, criteria_id)
);

CREATE TABLE IF NOT EXISTS ods_mag.admission_plan (
  program_name    VARCHAR PRIMARY KEY,
  budget_seats    INTEGER,
  contract_seats  INTEGER,
  updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ods_contracts_applicant  ON ods_mag.contracts(applicant_code);
CREATE INDEX IF NOT EXISTS idx_ods_contracts_program    ON ods_mag.contracts(program_name);
CREATE INDEX IF NOT EXISTS idx_ods_contracts_status     ON ods_mag.contracts(payment_status);
CREATE INDEX IF NOT EXISTS idx_ods_schedules_applicant  ON ods_mag.payment_schedules(applicant_code);
CREATE INDEX IF NOT EXISTS idx_ods_payments_contract    ON ods_mag.payments(contract_code);
CREATE INDEX IF NOT EXISTS idx_ods_payments_applicant   ON ods_mag.payments(applicant_code);
CREATE INDEX IF NOT EXISTS idx_ods_criteria_program     ON ods_mag.criteria(program_name);
