
CREATE SCHEMA IF NOT EXISTS mart_mag;

CREATE OR REPLACE VIEW mart_mag.v_mag_contracts AS
SELECT
  fc.contract_id,
  fc.ods_contract_code,
  fc.application_id,
  da.applicant_id,
  da.applicant_code,
  da.full_name,
  da.email,
  dp.program_id,
  dp.program_name,
  dp.specialization,
  dp.faculty,
  fc.payment_status,
  fc.discount_percent,
  fc.semester_cost,
  fc.total_sum,
  fc.has_files,
  fc.is_active,
  fc.valid_from,
  fc.valid_to,
  fc.is_current,
  fc.load_date
FROM dds_mag.fact_contracts fc
LEFT JOIN dds_mag.dim_applicants da ON fc.applicant_code = da.applicant_code
LEFT JOIN dds_mag.dim_programs   dp ON fc.program_name   = dp.program_name
WHERE fc.is_current = TRUE;

CREATE OR REPLACE VIEW mart_mag.v_mag_payments AS
SELECT
  fp.fact_payment_id,
  fp.payment_id,
  fp.contract_code,
  da.applicant_id,
  da.applicant_code,
  da.full_name,
  dp.program_name,
  dp.specialization,
  fp.payment_date,
  fp.payment_amount,
  fp.payment_name,
  fp.has_security_payment,
  fc.payment_status   AS contract_status,
  fc.discount_percent AS contract_discount,
  fp.valid_from,
  fp.valid_to,
  fp.is_current,
  fp.load_date
FROM dds_mag.fact_payments fp
LEFT JOIN dds_mag.dim_applicants da ON fp.applicant_code = da.applicant_code
LEFT JOIN dds_mag.fact_contracts  fc ON fp.contract_code  = fc.ods_contract_code AND fc.is_current = TRUE
LEFT JOIN dds_mag.dim_programs   dp ON fc.program_name   = dp.program_name
WHERE fp.is_current = TRUE;

CREATE OR REPLACE VIEW mart_mag.v_mag_admission_stats AS
SELECT
  dp.program_id,
  dp.program_name,
  dp.specialization,
  dp.faculty,
  fc.payment_status,
  COUNT(DISTINCT fc.applicant_code)    AS applicant_count,
  COUNT(*)                              AS contract_count,
  COALESCE(SUM(fc.total_sum), 0)       AS total_revenue,
  COALESCE(AVG(fc.discount_percent), 0) AS avg_discount,
  COALESCE(SUM(fc.semester_cost), 0)   AS total_semester_cost,
  dap.budget_seats,
  dap.contract_seats
FROM dds_mag.fact_contracts fc
LEFT JOIN dds_mag.dim_programs        dp  ON fc.program_name = dp.program_name
LEFT JOIN dds_mag.dim_admission_plans dap ON fc.program_name = dap.program_name
WHERE fc.is_current = TRUE
GROUP BY dp.program_id, dp.program_name, dp.specialization, dp.faculty,
         fc.payment_status, dap.budget_seats, dap.contract_seats;

CREATE OR REPLACE VIEW mart_mag.v_mag_contract_history AS
SELECT
  fc.contract_id,
  fc.ods_contract_code,
  fc.application_id,
  da.applicant_code,
  da.full_name,
  dp.program_name,
  dp.specialization,
  dp.faculty,
  fc.payment_status,
  fc.discount_percent,
  fc.semester_cost,
  fc.valid_from,
  fc.valid_to,
  fc.is_current,
  fc.load_date,
  ROW_NUMBER() OVER (
    PARTITION BY fc.ods_contract_code
    ORDER BY fc.valid_from ASC
  ) AS version_num
FROM dds_mag.fact_contracts fc
LEFT JOIN dds_mag.dim_applicants da ON fc.applicant_code = da.applicant_code
LEFT JOIN dds_mag.dim_programs   dp ON fc.program_name   = dp.program_name;

CREATE OR REPLACE VIEW mart_mag.v_mag_payment_schedule_summary AS
SELECT
  fps.fact_schedule_id,
  fps.schedule_code,
  fps.owner,
  da.applicant_code,
  da.full_name,
  fps.payment_status,
  fps.discount_value,
  COUNT(fp.fact_payment_id)                             AS payment_count,
  COALESCE(SUM(fp.payment_amount), 0)                  AS total_paid,
  COALESCE(MAX(fp.payment_date), '1900-01-01'::DATE)   AS last_payment_date,
  fps.valid_from,
  fps.valid_to,
  fps.is_current
FROM dds_mag.fact_payment_schedules fps
LEFT JOIN dds_mag.dim_applicants da  ON fps.applicant_code = da.applicant_code
LEFT JOIN dds_mag.fact_payments   fp ON fps.applicant_code = fp.applicant_code AND fp.is_current = TRUE
WHERE fps.is_current = TRUE
GROUP BY fps.fact_schedule_id, fps.schedule_code, fps.owner,
         da.applicant_code, da.full_name, fps.payment_status,
         fps.discount_value, fps.valid_from, fps.valid_to, fps.is_current;

CREATE OR REPLACE VIEW mart_mag.v_mag_applicant_summary AS
SELECT
  da.applicant_id,
  da.applicant_code,
  da.full_name,
  da.email,
  COUNT(DISTINCT CASE WHEN fc.is_current  THEN fc.contract_id END)  AS active_contracts,
  COUNT(DISTINCT CASE WHEN NOT fc.is_current THEN fc.contract_id END) AS closed_contracts,
  COUNT(DISTINCT CASE WHEN fp.is_current  THEN fp.fact_payment_id END) AS payments_count,
  STRING_AGG(DISTINCT dp.program_name, ', ')                         AS programs,
  COALESCE(SUM(CASE WHEN fp.is_current THEN fp.payment_amount END), 0) AS total_paid
FROM dds_mag.dim_applicants da
LEFT JOIN dds_mag.fact_contracts fc ON da.applicant_code = fc.applicant_code
LEFT JOIN dds_mag.fact_payments  fp ON da.applicant_code = fp.applicant_code
LEFT JOIN dds_mag.dim_programs   dp ON fc.program_name   = dp.program_name
GROUP BY da.applicant_id, da.applicant_code, da.full_name, da.email;
