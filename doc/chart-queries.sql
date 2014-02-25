-- sample queries to generate historical graphs
-- graphed data in the examples: disk usage

-- Depends: Postgres (due to "DISTINCT ON")


-- last month
SELECT DISTINCT ON (date_trunc('hour', timestamp)) timestamp, disk_usage AS value
FROM history_size
WHERE timestamp >= now() - interval '1 year'
-- AND SUITE = '...'
ORDER BY date_trunc('hour', timestamp) DESC, timestamp DESC;

-- last year graph
SELECT DISTINCT ON (date_trunc('day', timestamp)) timestamp, disk_usage AS value
FROM history_size
WHERE timestamp >= now() - interval '1 year'
-- AND SUITE = '...'
ORDER BY date_trunc('day', timestamp) DESC, timestamp DESC;


-- last 5-years graph
SELECT DISTINCT ON (date_trunc('week', timestamp)) timestamp, disk_usage AS value
FROM history_size
WHERE timestamp >= now() - interval '5 year'
-- AND SUITE = '...'
ORDER BY date_trunc('week', timestamp) DESC, timestamp DESC;


-- last 20-years graph
SELECT DISTINCT ON (date_trunc('month', timestamp)) timestamp, disk_usage AS value
FROM history_size
WHERE timestamp >= now() - interval '20 year'
-- AND SUITE = '...'
ORDER BY date_trunc('month', timestamp) DESC, timestamp DESC;
