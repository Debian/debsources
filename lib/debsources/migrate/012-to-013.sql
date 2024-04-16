-- Remove size constraint on packages.area
-- From varchar(8) to varchar
-- This allows "non-free-firmware"

ALTER TABLE packages ALTER COLUMN area TYPE varchar;
