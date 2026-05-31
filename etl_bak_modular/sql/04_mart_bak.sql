
DROP SCHEMA IF EXISTS mart_bak CASCADE;
CREATE SCHEMA mart_bak;

CREATE OR REPLACE VIEW mart_bak.v_applications AS
SELECT
    fa.app_id,
    da.code_applicant,
    da.full_name,
    da.city,
    dp.program,
    dp.specialization,
    fa.priority,
    fa.sspvo_status,
    fa.reg_number,
    fa.valid_from   AS load_date
FROM dds_bak.fact_applications fa
JOIN dds_bak.dim_applicants da ON da.applicant_id = fa.applicant_id
JOIN dds_bak.dim_programs   dp ON dp.program_id   = fa.program_id
WHERE fa.is_current = TRUE;

CREATE OR REPLACE VIEW mart_bak.v_contracts AS
SELECT
    fc.dogovor,
    fc.contract_date,
    da.code_applicant,
    da.full_name,
    da.city,
    dp.program,
    dp.specialization,
    fc.priority,
    fc.payment_status,
    fc.admission_plan,
    fc.ege,
    fc.bvi,
    fc.individual_achievements,
    fc.total,
    fc.name_parent,
    fc.number_parent,
    fc.valid_from   AS load_date
FROM dds_bak.fact_contracts fc
JOIN dds_bak.dim_applicants da ON da.applicant_id = fc.applicant_id
JOIN dds_bak.dim_programs   dp ON dp.program_id   = fc.program_id
WHERE fc.is_current = TRUE;

CREATE OR REPLACE VIEW mart_bak.v_scores AS
SELECT
    fs.nomer,
    da.code_applicant,
    da.full_name,
    da.city,
    dp.program,
    dp.specialization,
    fs.priority,
    fs.score_without_vi,
    fs.all_vi_passed,
    fs.rank1, fs.rank2, fs.rank3, fs.rank4,
    fs.rank5, fs.rank6, fs.rank13,
    fs.valid_from   AS load_date
FROM dds_bak.fact_scores fs
JOIN dds_bak.dim_applicants da ON da.applicant_id = fs.applicant_id
JOIN dds_bak.dim_programs   dp ON dp.program_id   = fs.program_id
WHERE fs.is_current = TRUE;

CREATE OR REPLACE VIEW mart_bak.v_payment_summary AS
SELECT
    dp.program,
    dp.specialization,
    dp.city,
    fc.payment_status,
    COUNT(*)        AS contracts,
    SUM(fc.total)   AS total_sum,
    AVG(fc.total)   AS avg_sum
FROM dds_bak.fact_contracts fc
JOIN dds_bak.dim_programs dp ON dp.program_id = fc.program_id
WHERE fc.is_current = TRUE
GROUP BY dp.program, dp.specialization, dp.city, fc.payment_status;

CREATE OR REPLACE VIEW mart_bak.v_admission_stats AS
SELECT
    dp.program,
    dp.specialization,
    dp.city,
    COALESCE(fa.applicants, 0) AS applicants,
    COALESCE(fc.contracts,    0) AS contracts,
    fs.best_rank2,
    fs.worst_rank2,
    fs.avg_rank2
FROM dds_bak.dim_programs dp
LEFT JOIN (
    SELECT program_id,
           COUNT(DISTINCT applicant_id) AS applicants
    FROM dds_bak.fact_applications
    WHERE is_current = TRUE
    GROUP BY program_id
) fa ON fa.program_id = dp.program_id
LEFT JOIN (
    SELECT program_id,
           COUNT(DISTINCT contract_dds_id) AS contracts
    FROM dds_bak.fact_contracts
    WHERE is_current = TRUE
    GROUP BY program_id
) fc ON fc.program_id = dp.program_id
LEFT JOIN (
    SELECT program_id,
           MIN(rank2)                      AS best_rank2,
           MAX(rank2)                      AS worst_rank2,
           ROUND(AVG(rank2)::NUMERIC, 2)   AS avg_rank2
    FROM dds_bak.fact_scores
    WHERE is_current = TRUE
    GROUP BY program_id
) fs ON fs.program_id = dp.program_id;

CREATE OR REPLACE VIEW mart_bak.v_contract_history AS
SELECT
    fc.dogovor,
    fc.contract_date,
    da.code_applicant,
    da.full_name,
    dp.program,
    fc.payment_status,
    fc.total,
    fc.valid_from,
    fc.valid_to,
    fc.is_current
FROM dds_bak.fact_contracts fc
JOIN dds_bak.dim_applicants da ON da.applicant_id = fc.applicant_id
JOIN dds_bak.dim_programs   dp ON dp.program_id   = fc.program_id
ORDER BY fc.dogovor, fc.valid_from;

COMMENT ON SCHEMA mart_bak IS 'MART: аналитические витрины для отчётности';
