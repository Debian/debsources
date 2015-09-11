CREATE TYPE copyright_oracles as ENUM(
    'debian'
);

CREATE TABLE copyright (
  id SERIAL NOT NULL,
  file_id INTEGER NOT NULL,
  oracle copyright_oracles NOT NULL,
  license VARCHAR,
  CONSTRAINT copyright_file_id_fkey
    FOREIGN KEY (file_id) REFERENCES files(id)
    ON DELETE CASCADE,
  PRIMARY KEY (id)
);

CREATE INDEX ix_copyright_file_id ON copyright (file_id);
