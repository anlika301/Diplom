

DROP SCHEMA IF EXISTS stg_bak CASCADE;
CREATE SCHEMA stg_bak;

CREATE TABLE stg_bak.applications (
    id                              TEXT PRIMARY KEY,
    load_date   DATE,
    source_file TEXT DEFAULT 'application_bak_rows.csv',

    city                            TEXT,
    full_name                       TEXT,
    code_applicant                  TEXT,
    priority                        TEXT,
    specialization                  TEXT,
    program                         TEXT,
    reg_number                      TEXT,
    uniq_code                       TEXT,
    sspvo_status                    TEXT
);

CREATE INDEX ON stg_bak.applications (load_date);
CREATE INDEX ON stg_bak.applications (code_applicant);

CREATE TABLE stg_bak.scores (
    nomer                           TEXT PRIMARY KEY, 
    load_date   DATE,
    source_file TEXT DEFAULT 'ball_bak_rows.csv',

    full_name                       TEXT,
    code_applicant                  TEXT,
    priority                        TEXT,
    specialization                  TEXT,
    program                         TEXT,
    city                            TEXT,
    score_without_vi                TEXT,
    all_vi_passed                   TEXT,
    rank1                           TEXT,
    rank2                           TEXT,
    rank3                           TEXT,
    rank4                           TEXT,
    rank5                           TEXT,
    rank6                           TEXT,
    rank7                           TEXT,
    rank8                           TEXT,
    rank9                           TEXT,
    rank10                          TEXT,
    rank11                          TEXT,
    rank12                          TEXT,
    rank13                          TEXT
);

CREATE INDEX ON stg_bak.scores (load_date);
CREATE INDEX ON stg_bak.scores (code_applicant);
CREATE INDEX ON stg_bak.scores (nomer);

CREATE TABLE stg_bak.contracts (
    dogovor                         TEXT PRIMARY KEY,
    contract_date                   DATE,
    load_date   DATE,
    source_file TEXT DEFAULT 'dogovor_bak_rows.csv',

    full_name                       TEXT,
    code_applicant                  TEXT,
    uniq_code                       TEXT,
    city                            TEXT,
    payment_status                  TEXT,
    name_parent                     TEXT,
    number_parent                   TEXT,
    specialization                  TEXT,
    id_application                  TEXT,
    program                         TEXT,
    priority                        TEXT,
    admission_plan                  TEXT,
    bvi                             TEXT,
    ege                             TEXT,
    individual_achievements         TEXT,
    total                           TEXT
);

CREATE INDEX ON stg_bak.contracts (load_date);
CREATE INDEX ON stg_bak.contracts (code_applicant);
CREATE INDEX ON stg_bak.contracts (dogovor);

CREATE TABLE stg_bak.criteria (
    scep                            TEXT PRIMARY KEY,
    load_date   DATE,
    source_file TEXT DEFAULT 'kriterii_bak_rows.csv',

    direction                       TEXT,
    program_name                    TEXT,
    criteria_value                  TEXT
);

CREATE INDEX ON stg_bak.criteria (load_date);
CREATE INDEX ON stg_bak.criteria (program_name);

COMMENT ON SCHEMA stg_bak IS 'Staging: сырые CSV данные, append-only';
