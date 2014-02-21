CREATE TABLE history_sloccount (
  timestamp TIMESTAMP WITHOUT TIME ZONE NOT NULL,
  suite VARCHAR NOT NULL,
  lang_ada INTEGER,
  lang_ansic INTEGER,
  lang_asm INTEGER,
  lang_awk INTEGER,
  lang_cobol INTEGER,
  lang_cpp INTEGER,
  lang_cs INTEGER,
  lang_csh INTEGER,
  lang_erlang INTEGER,
  lang_exp INTEGER,
  lang_f90 INTEGER,
  lang_fortran INTEGER,
  lang_haskell INTEGER,
  lang_java INTEGER,
  lang_jsp INTEGER,
  lang_lex INTEGER,
  lang_lisp INTEGER,
  lang_makefile INTEGER,
  lang_ml INTEGER,
  lang_modula3 INTEGER,
  lang_objc INTEGER,
  lang_pascal INTEGER,
  lang_perl INTEGER,
  lang_php INTEGER,
  lang_python INTEGER,
  lang_ruby INTEGER,
  lang_sed INTEGER,
  lang_sh INTEGER,
  lang_sql INTEGER,
  lang_tcl INTEGER,
  lang_vhdl INTEGER,
  lang_xml INTEGER,
  lang_yacc INTEGER,
  PRIMARY KEY (timestamp, suite)
);

CREATE INDEX ix_history_sloccount_timestamp ON history_sloccount (timestamp);

CREATE TABLE history_size (
  timestamp TIMESTAMP WITHOUT TIME ZONE NOT NULL,
  suite VARCHAR NOT NULL,
  source_packages INTEGER,
  binary_packages INTEGER,
  disk_usage INTEGER,
  source_files INTEGER,
  ctags INTEGER,
  PRIMARY KEY (timestamp, suite)
);

CREATE INDEX ix_history_size_timestamp ON history_size (timestamp);
