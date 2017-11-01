CREATE TABLE suites_aliases (
  alias VARCHAR NOT NULL,
  suite VARCHAR NOT NULL,
  CONSTRAINT suites_aliases_alias_suite_key
    UNIQUE(alias),
  CONSTRAINT suites_aliases_suite_fkey
    FOREIGN KEY (suite) REFERENCES suites_info(name)
    ON DELETE CASCADE,
  PRIMARY KEY (alias, suite)
);
