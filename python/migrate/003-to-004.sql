CREATE INDEX ix_versions_vnumber ON versions (vnumber);

CREATE INDEX ix_history_size_suite ON history_size (suite);
CREATE INDEX ix_history_sloccount_suite ON history_sloccount (suite);
