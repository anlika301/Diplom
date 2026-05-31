

DROP SCHEMA IF EXISTS dds_bak CASCADE;
CREATE SCHEMA dds_bak;

CREATE TABLE dds_bak.dim_applicants (
    applicant_id    BIGSERIAL PRIMARY KEY,
    code_applicant  TEXT UNIQUE NOT NULL,

    full_name       TEXT,
    city            TEXT,
    uniq_code       TEXT,

    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX ON dds_bak.dim_applicants (code_applicant);

CREATE TABLE dds_bak.dim_programs (
    program_id      BIGSERIAL PRIMARY KEY,

    program         TEXT,
    specialization  TEXT,
    city            TEXT,

    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW(),

    UNIQUE (program, specialization, city)
);

CREATE INDEX ON dds_bak.dim_programs (program);

CREATE TABLE dds_bak.dim_criteria (
    criteria_id     BIGSERIAL PRIMARY KEY,
    program_id      BIGINT NOT NULL REFERENCES dds_bak.dim_programs (program_id),
    scep            TEXT UNIQUE NOT NULL,

    direction       TEXT,
    criteria_value  TEXT,

    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX ON dds_bak.dim_criteria (program_id);
CREATE INDEX ON dds_bak.dim_criteria (scep);

CREATE TABLE dds_bak.fact_applications (
    application_dds_id  BIGSERIAL PRIMARY KEY,
    app_id              TEXT,
    applicant_id        BIGINT NOT NULL REFERENCES dds_bak.dim_applicants (applicant_id),
    program_id          BIGINT NOT NULL REFERENCES dds_bak.dim_programs (program_id),

    valid_from          DATE,
    valid_to            DATE,
    is_current          BOOLEAN DEFAULT TRUE,

    priority            INTEGER,
    reg_number          TEXT,
    uniq_code           TEXT,
    sspvo_status        TEXT,

    created_at          TIMESTAMP DEFAULT NOW()
);

CREATE INDEX ON dds_bak.fact_applications (app_id);
CREATE INDEX ON dds_bak.fact_applications (applicant_id);
CREATE INDEX ON dds_bak.fact_applications (program_id);
CREATE INDEX ON dds_bak.fact_applications (is_current) WHERE is_current = TRUE;

CREATE TABLE dds_bak.fact_scores (
    score_dds_id        BIGSERIAL PRIMARY KEY,
    nomer               TEXT,
    applicant_id        BIGINT NOT NULL REFERENCES dds_bak.dim_applicants (applicant_id),
    program_id          BIGINT NOT NULL REFERENCES dds_bak.dim_programs (program_id),

    valid_from          DATE,
    valid_to            DATE,
    is_current          BOOLEAN DEFAULT TRUE,

    priority            INTEGER,
    score_without_vi    INTEGER,
    all_vi_passed       BOOLEAN,

    rank1               NUMERIC(10,4),
    rank2               NUMERIC(10,4),
    rank3               NUMERIC(10,4),
    rank4               NUMERIC(10,4),
    rank5               NUMERIC(10,4),
    rank6               NUMERIC(10,4),
    rank7               NUMERIC(10,4),
    rank8               NUMERIC(10,4),
    rank9               NUMERIC(10,4),
    rank10              NUMERIC(10,4),
    rank11              NUMERIC(10,4),
    rank12              NUMERIC(10,4),
    rank13              NUMERIC(10,4),

    created_at          TIMESTAMP DEFAULT NOW()
);

CREATE INDEX ON dds_bak.fact_scores (nomer);
CREATE INDEX ON dds_bak.fact_scores (applicant_id);
CREATE INDEX ON dds_bak.fact_scores (program_id);
CREATE INDEX ON dds_bak.fact_scores (is_current) WHERE is_current = TRUE;

CREATE TABLE dds_bak.fact_contracts (
    contract_dds_id     BIGSERIAL PRIMARY KEY,
    dogovor             TEXT,
    contract_date       DATE,
    applicant_id        BIGINT NOT NULL REFERENCES dds_bak.dim_applicants (applicant_id),
    program_id          BIGINT NOT NULL REFERENCES dds_bak.dim_programs (program_id),

    valid_from          DATE,
    valid_to            DATE,
    is_current          BOOLEAN DEFAULT TRUE,

    id_application          TEXT,
    priority                INTEGER,
    admission_plan          TEXT,
    payment_status          TEXT,
    name_parent             TEXT,
    number_parent           TEXT,
    bvi                     TEXT,
    ege                     INTEGER,
    individual_achievements INTEGER,
    total                   NUMERIC(14,2),
    uniq_code               TEXT,

    created_at              TIMESTAMP DEFAULT NOW()
);

CREATE INDEX ON dds_bak.fact_contracts (dogovor);
CREATE INDEX ON dds_bak.fact_contracts (applicant_id);
CREATE INDEX ON dds_bak.fact_contracts (program_id);
CREATE INDEX ON dds_bak.fact_contracts (payment_status);
CREATE INDEX ON dds_bak.fact_contracts (is_current) WHERE is_current = TRUE;

COMMENT ON SCHEMA dds_bak IS 'DDS: 3NF нормализация + SCD Type 2 историзация';
