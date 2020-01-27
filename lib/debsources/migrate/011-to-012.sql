-- adds javascript support for sloccount:
-- - new column in table sloccount_history
-- - new enum value used by table sloccount

ALTER TABLE history_sloccount
	ADD COLUMN lang_javascript bigint;

ALTER TYPE language_names ADD VALUE 'javascript';
