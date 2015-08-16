CREATE TABLE copyright (
  id SERIAL NOT NULL,
  file_id INTEGER NOT NULL,
  oracle VARCHAR NOT NULL,
  license VARCHAR,
  CONSTRAINT copyright_file_id_fkey
    FOREIGN KEY (file_id) REFERENCES files(id)
    ON DELETE CASCADE,
  PRIMARY KEY (id)
);
