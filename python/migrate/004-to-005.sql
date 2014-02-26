ALTER TABLE versions
  ADD COLUMN sticky BOOLEAN;

UPDATE versions SET sticky = FALSE;

ALTER TABLE versions
  ALTER COLUMN sticky SET NOT NULL;
