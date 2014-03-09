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
ALTER TABLE versions
  RENAME COLUMN package_id TO name_id ;
-- see below
-- ALTER INDEX ix_versions_package_id
--   RENAME TO ix_versions_name_id ;

ALTER TABLE versions RENAME TO packages ;
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
