ALTER TABLE versions
  RENAME COLUMN vnumber TO version ;
ALTER INDEX ix_versions_package_id_vnumber
  RENAME TO ix_versions_package_id_version ;

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
