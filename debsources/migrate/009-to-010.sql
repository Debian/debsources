CREATE TABLE history_copyright (
  id SERIAL NOT NULL,
  timestamp TIMESTAMP WITHOUT TIME ZONE NOT NULL,
  suite VARCHAR NOT NULL,
  license VARCHAR,
  files INTEGER,
);
