ALTER TABLE versions
  RENAME COLUMN vnumber TO version ;
-- see below
-- ALTER INDEX ix_versions_vnumber
--   RENAME TO ix_versions_version ;
-- see below
-- ALTER INDEX ix_versions_package_id_vnumber
--   RENAME TO ix_versions_package_id_version ;

ALTER TABLE suitesmapping
  RENAME COLUMN sourceversion_id TO version_id ;
ALTER INDEX ix_binaryversions_sourceversion_id
  RENAME TO ix_binaryversions_version_id ;
ALTER INDEX ix_metrics_sourceversion_id
  RENAME TO ix_metrics_version_id ;
ALTER INDEX ix_sloccounts_sourceversion_id
  RENAME TO ix_sloccounts_version_id ;
ALTER INDEX ix_suitesmapping_sourceversion_id
  RENAME TO ix_suitesmapping_version_id ;
ALTER INDEX metrics_sourceversion_id_metric_key
  RENAME TO metrics_version_id_metric_key ;
ALTER INDEX sloccounts_sourceversion_id_language_key
  RENAME TO sloccounts_version_id_language_key ;
ALTER INDEX suitesmapping_sourceversion_id_suite_key
  RENAME TO suitesmapping_version_id_suite_key ;

ALTER TABLE suites RENAME TO suites_info ;
ALTER INDEX suites_pkey RENAME TO suites_info_pkey ;

ALTER TABLE packages RENAME TO package_names ;
ALTER INDEX packages_pkey
  RENAME TO package_names_pkey ;
ALTER SEQUENCE packages_id_seq
  RENAME TO package_names_id_seq ;

ALTER TABLE versions
  RENAME COLUMN package_id TO name_id ;
-- see below
-- ALTER INDEX ix_versions_package_id
--   RENAME TO ix_versions_name_id ;

ALTER TABLE versions RENAME TO packages ;
ALTER SEQUENCE versions_id_seq
  RENAME TO packages_id_seq ;
ALTER INDEX ix_versions_package_id_vnumber
  RENAME TO ix_packages_name_id_version ;
ALTER INDEX ix_versions_area
  RENAME TO ix_packages_area ;
ALTER INDEX ix_versions_package_id
  RENAME TO ix_packages_name_id ;
ALTER INDEX ix_versions_vnumber
  RENAME TO ix_packages_version ;
ALTER INDEX versions_pkey
  RENAME TO packages_pkey ;
ALTER INDEX files_version_id_path_key
  RENAME TO files_package_id_path_key ;
ALTER INDEX ix_binaryversions_version_id
  RENAME TO ix_binaryversions_package_id ;
ALTER INDEX ix_checksums_version_id
  RENAME TO ix_checksums_package_id ;
ALTER INDEX checksums_version_id_file_id_key
  RENAME TO checksums_package_id_file_id_key ;
ALTER INDEX ix_ctags_version_id
  RENAME TO ix_ctags_package_id ;
ALTER INDEX ix_files_version_id
  RENAME TO ix_files_package_id ;
ALTER INDEX ix_metrics_version_id
  RENAME TO ix_metrics_package_id ;
ALTER INDEX ix_sloccounts_version_id
  RENAME TO ix_sloccounts_package_id ;
ALTER INDEX ix_suitesmapping_version_id
  RENAME TO ix_suitesmapping_package_id;
ALTER INDEX metrics_version_id_metric_key
  RENAME TO metrics_package_id_metric_key ;
ALTER INDEX sloccounts_version_id_language_key
  RENAME TO sloccounts_package_id_language_key ;
ALTER INDEX suitesmapping_version_id_suite_key
  RENAME TO suitesmapping_package_id_suite_key ;

ALTER TABLE checksums RENAME COLUMN version_id TO package_id ;
ALTER TABLE ctags RENAME COLUMN version_id TO package_id ;
ALTER TABLE files RENAME COLUMN version_id TO package_id ;
ALTER TABLE metrics RENAME COLUMN sourceversion_id TO package_id ;
ALTER TABLE sloccounts RENAME COLUMN sourceversion_id TO package_id ;
ALTER TABLE suitesmapping RENAME COLUMN version_id TO package_id ;

ALTER TABLE suitesmapping RENAME TO suites ;
ALTER SEQUENCE suitesmapping_id_seq RENAME TO suites_id_seq ;
ALTER INDEX ix_suitesmapping_package_id RENAME TO ix_suites_package_id ;
ALTER INDEX ix_suitesmapping_suite RENAME TO ix_suites_suite ;
ALTER INDEX suitesmapping_package_id_suite_key
  RENAME TO suites_package_id_suite_key ;
ALTER INDEX suitesmapping_pkey RENAME TO suites_pkey ;
ALTER INDEX binarypackages_pkey RENAME TO binary_names_pkey ;
ALTER INDEX binaryversions_pkey RENAME TO binaries_pkey ;

ALTER TABLE binaryversions
  RENAME COLUMN vnumber TO version ;
ALTER TABLE binaryversions
  RENAME COLUMN sourceversion_id TO package_id ;

ALTER TABLE binarypackages RENAME TO binary_names ;
ALTER TABLE binaryversions RENAME TO binaries ;
ALTER TABLE binaries RENAME COLUMN binarypackage_id TO name_id ;
ALTER SEQUENCE binarypackages_id_seq RENAME TO binary_names_id_seq ;
ALTER SEQUENCE binaryversions_id_seq RENAME TO binaries_id_seq ;
ALTER INDEX ix_binarypackages_name RENAME TO ix_binary_names_name ;
ALTER INDEX ix_binaryversions_binarypackage_id RENAME TO ix_binaries_name_id ;
ALTER INDEX ix_binaryversions_package_id RENAME TO ix_binaries_package_id ;
