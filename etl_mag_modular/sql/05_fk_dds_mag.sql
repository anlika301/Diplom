
ALTER TABLE dds_mag.fact_contracts
  ADD CONSTRAINT fk_fact_contracts_applicant
  FOREIGN KEY (applicant_code) REFERENCES dds_mag.dim_applicants (applicant_code)
  ON UPDATE CASCADE ON DELETE RESTRICT;

ALTER TABLE dds_mag.fact_payment_schedules
  ADD CONSTRAINT fk_fact_schedules_applicant
  FOREIGN KEY (applicant_code) REFERENCES dds_mag.dim_applicants (applicant_code)
  ON UPDATE CASCADE ON DELETE RESTRICT;

ALTER TABLE dds_mag.fact_payments
  ADD CONSTRAINT fk_fact_payments_applicant
  FOREIGN KEY (applicant_code) REFERENCES dds_mag.dim_applicants (applicant_code)
  ON UPDATE CASCADE ON DELETE RESTRICT;

ALTER TABLE dds_mag.fact_contracts
  ADD CONSTRAINT fk_fact_contracts_program
  FOREIGN KEY (program_name) REFERENCES dds_mag.dim_programs (program_name)
  ON UPDATE CASCADE ON DELETE RESTRICT;

ALTER TABLE dds_mag.dim_admission_plans
  ADD CONSTRAINT fk_dim_plans_program
  FOREIGN KEY (program_name) REFERENCES dds_mag.dim_programs (program_name)
  ON UPDATE CASCADE ON DELETE RESTRICT;

ALTER TABLE dds_mag.dim_criteria
  ADD CONSTRAINT fk_dim_criteria_program
  FOREIGN KEY (program_name) REFERENCES dds_mag.dim_programs (program_name)
  ON UPDATE CASCADE ON DELETE RESTRICT;
