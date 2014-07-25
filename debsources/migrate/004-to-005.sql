ALTER TABLE versions
  ADD COLUMN sticky BOOLEAN;

UPDATE versions SET sticky = FALSE;

ALTER TABLE versions
  ALTER COLUMN sticky SET NOT NULL;

ALTER TABLE suitesmapping
  ADD CONSTRAINT suitesmapping_sourceversion_id_suite_key
    UNIQUE (sourceversion_id, suite);

CREATE TABLE suites (
  name VARCHAR NOT NULL,
  release_date DATE,
  sticky BOOLEAN NOT NULL,
  PRIMARY KEY (name)
);
