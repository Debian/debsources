ALTER TABLE versions RENAME COLUMN vnumber TO version ;
ALTER INDEX ix_versions_package_id_vnumber
  RENAME TO ix_versions_package_id_version ;
