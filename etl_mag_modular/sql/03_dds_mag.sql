
CREATE SCHEMA IF NOT EXISTS dds_mag;


CREATE TABLE IF NOT EXISTS dds_mag.dim_applicants (
  applicant_id    BIGSERIAL PRIMARY KEY,
  applicant_code  VARCHAR UNIQUE NOT NULL,
  full_name       TEXT,
  email           TEXT,
  updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_dim_applicants_code ON dds_mag.dim_applicants(applicant_code);

CREATE TABLE IF NOT EXISTS dds_mag.dim_programs (
  program_id     BIGSERIAL PRIMARY KEY,
  program_name   TEXT UNIQUE NOT NULL,
  specialization TEXT,
  faculty        TEXT,
  updated_at     TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_dim_programs_name ON dds_mag.dim_programs(program_name);

CREATE TABLE IF NOT EXISTS dds_mag.dim_admission_plans (
  plan_id         BIGSERIAL PRIMARY KEY,
  program_name    TEXT UNIQUE NOT NULL,
  budget_seats    INTEGER,
  contract_seats  INTEGER,
  updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_dim_plans_program ON dds_mag.dim_admission_plans(program_name);

CREATE TABLE IF NOT EXISTS dds_mag.dim_criteria (
  dim_criteria_id  BIGSERIAL PRIMARY KEY,
  program_name     TEXT NOT NULL,
  criteria_id      INTEGER,
  updated_at       TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (program_name, criteria_id)
);

CREATE INDEX IF NOT EXISTS idx_dim_criteria_program ON dds_mag.dim_criteria(program_name);


CREATE TABLE IF NOT EXISTS dds_mag.fact_contracts (
  contract_id       BIGSERIAL PRIMARY KEY,
  ods_contract_code VARCHAR NOT NULL,
  applicant_code    VARCHAR REFERENCES dds_mag.dim_applicants (applicant_code) ON UPDATE CASCADE ON DELETE RESTRICT,
  program_name      TEXT REFERENCES dds_mag.dim_programs (program_name) ON UPDATE CASCADE ON DELETE RESTRICT,
  application_id    VARCHAR,
  contract_date     DATE,
  has_files         BOOLEAN,
  is_active         INTEGER,
  payment_status    TEXT,
  discount_percent  DECIMAL,
  semester_cost     DECIMAL,
  total_sum         DECIMAL,
  valid_from        DATE NOT NULL,
  valid_to          DATE,
  is_current        BOOLEAN DEFAULT TRUE,
  load_date         DATE
);

CREATE INDEX IF NOT EXISTS idx_fact_contracts_code    ON dds_mag.fact_contracts(ods_contract_code);
CREATE INDEX IF NOT EXISTS idx_fact_contracts_appl    ON dds_mag.fact_contracts(applicant_code, is_current);
CREATE INDEX IF NOT EXISTS idx_fact_contracts_program ON dds_mag.fact_contracts(program_name, is_current);
CREATE INDEX IF NOT EXISTS idx_fact_contracts_current ON dds_mag.fact_contracts(is_current);

CREATE TABLE IF NOT EXISTS dds_mag.fact_payment_schedules (
  fact_schedule_id  BIGSERIAL PRIMARY KEY,
  schedule_code     VARCHAR NOT NULL,
  applicant_code    VARCHAR REFERENCES dds_mag.dim_applicants (applicant_code) ON UPDATE CASCADE ON DELETE RESTRICT,
  owner             TEXT,
  discount_value    DECIMAL,
  payment_status    TEXT,
  valid_from        DATE NOT NULL,
  valid_to          DATE,
  is_current        BOOLEAN DEFAULT TRUE,
  load_date         DATE
);

CREATE INDEX IF NOT EXISTS idx_fact_schedules_code    ON dds_mag.fact_payment_schedules(schedule_code);
CREATE INDEX IF NOT EXISTS idx_fact_schedules_appl    ON dds_mag.fact_payment_schedules(applicant_code, is_current);
CREATE INDEX IF NOT EXISTS idx_fact_schedules_current ON dds_mag.fact_payment_schedules(is_current);

CREATE TABLE IF NOT EXISTS dds_mag.fact_payments (
  fact_payment_id      BIGSERIAL PRIMARY KEY,
  payment_id           VARCHAR NOT NULL,
  applicant_code       VARCHAR REFERENCES dds_mag.dim_applicants (applicant_code) ON UPDATE CASCADE ON DELETE RESTRICT,
  contract_code        VARCHAR,
  payment_date         DATE,
  payment_amount       DECIMAL,
  payment_name         TEXT,
  has_security_payment BOOLEAN,
  valid_from           DATE NOT NULL,
  valid_to             DATE,
  is_current           BOOLEAN DEFAULT TRUE,
  load_date            DATE
);

CREATE INDEX IF NOT EXISTS idx_fact_payments_pid     ON dds_mag.fact_payments(payment_id);
CREATE INDEX IF NOT EXISTS idx_fact_payments_appl    ON dds_mag.fact_payments(applicant_code, is_current);
CREATE INDEX IF NOT EXISTS idx_fact_payments_contract ON dds_mag.fact_payments(contract_code);
CREATE INDEX IF NOT EXISTS idx_fact_payments_date    ON dds_mag.fact_payments(payment_date);
CREATE INDEX IF NOT EXISTS idx_fact_payments_current ON dds_mag.fact_payments(is_current);
