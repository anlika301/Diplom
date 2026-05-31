
DROP SCHEMA IF EXISTS ods_bak CASCADE;
CREATE SCHEMA ods_bak;

CREATE TABLE ods_bak.applications (
    app_id          TEXT PRIMARY KEY,
    load_date       DATE,
    updated_at      TIMESTAMP DEFAULT NOW(),

    full_name       TEXT,
    code_applicant  TEXT,
    city            TEXT,
    specialization  TEXT,
    program         TEXT,
    priority        INTEGER,
    reg_number      TEXT,
    uniq_code       TEXT,
    sspvo_status    TEXT
);

CREATE INDEX ON ods_bak.applications (code_applicant);
CREATE INDEX ON ods_bak.applications (program);
CREATE INDEX ON ods_bak.applications (load_date);

CREATE TABLE ods_bak.scores (
    nomer               TEXT PRIMARY KEY,
    load_date           DATE,
    updated_at          TIMESTAMP DEFAULT NOW(),

    full_name           TEXT,
    code_applicant      TEXT,
    city                TEXT,
    specialization      TEXT,
    program             TEXT,
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
    rank13              NUMERIC(10,4)
);

CREATE INDEX ON ods_bak.scores (code_applicant);
CREATE INDEX ON ods_bak.scores (program);
CREATE INDEX ON ods_bak.scores (load_date);

CREATE TABLE ods_bak.contracts (
    dogovor                 TEXT PRIMARY KEY,
    contract_date           DATE,
    load_date               DATE,
    updated_at              TIMESTAMP DEFAULT NOW(),

    full_name               TEXT,
    code_applicant          TEXT,
    uniq_code               TEXT,
    city                    TEXT,
    specialization          TEXT,
    program                 TEXT,
    id_application          TEXT,
    priority                INTEGER,
    admission_plan          TEXT,
    payment_status          TEXT,
    name_parent             TEXT,
    number_parent           TEXT,
    bvi                     TEXT,
    ege                     INTEGER,
    individual_achievements INTEGER,
    total                   NUMERIC(14,2)
);

CREATE INDEX ON ods_bak.contracts (code_applicant);
CREATE INDEX ON ods_bak.contracts (program);
CREATE INDEX ON ods_bak.contracts (payment_status);
CREATE INDEX ON ods_bak.contracts (load_date);

CREATE TABLE ods_bak.criteria (
    scep            TEXT PRIMARY KEY,
    load_date       DATE,
    updated_at      TIMESTAMP DEFAULT NOW(),

    direction       TEXT,
    program_name    TEXT,
    criteria_value  TEXT
);

CREATE INDEX ON ods_bak.criteria (program_name);

COMMENT ON SCHEMA ods_bak IS 'ODS: текущее состояние, UPSERT по натуральному ключу';
