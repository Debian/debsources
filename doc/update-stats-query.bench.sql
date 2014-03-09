-- one suite: ctags
SELECT count(ctags.id)
FROM ctags, versions, suitesmapping
WHERE ctags.package_id = versions.id
AND   versions.id = suitesmapping.package_id
AND   suitesmapping.suite = 'jessie'
;
--   count   
-- ----------
--  82769666
-- (1 row)
-- Time: 100 166,175 ms

-- all suites: ctags
SELECT count(ctags.id), suitesmapping.suite
FROM ctags, versions, suitesmapping
WHERE ctags.package_id = versions.id
AND   versions.id = suitesmapping.package_id
GROUP BY suitesmapping.suite
;
--    count   |          suite          
-- -----------+-------------------------
--   28998896 | etch
--    3923385 | hamm
--    5937366 | slink
--   45203464 | wheezy
--   30754018 | squeeze
--  106934528 | sid
--      15237 | wheezy-updates
--   22902109 | sarge
--   12996912 | experimental
--   82769666 | jessie
--    6837056 | potato
--    2132206 | wheezy-proposed-updates
--   36487649 | lenny
--      47470 | squeeze-updates
--   11253095 | wheezy-backports
--   16641412 | woody
-- (16 rows)
-- Time: 365 316,324 ms

-- one suite: files
SELECT count(files.id)    
FROM files, versions, suitesmapping
WHERE files.package_id = versions.id
AND   versions.id = suitesmapping.package_id
AND   suitesmapping.suite = 'sid'
;
--   count  
-- ---------
--  9879916
-- (1 row)
-- Time: 11 338,649 ms

-- all suites: files
SELECT count(files.id), suitesmapping.suite
FROM files, versions, suitesmapping
WHERE files.package_id = versions.id
AND   versions.id = suitesmapping.package_id
GROUP BY suitesmapping.suite
;
--   count  |          suite          
-- ---------+-------------------------
--  2885727 | etch
--   348606 | hamm
--   484248 | slink
--  6588073 | wheezy
--  4913222 | squeeze
--  9879916 | sid
--     2262 | wheezy-updates
--  2396899 | sarge
--  1460211 | experimental
--  8003212 | jessie
--   659377 | potato
--   141958 | wheezy-proposed-updates
--  3719995 | lenny
--     2415 | squeeze-updates
--   925521 | wheezy-backports
--  1399194 | woody
-- (16 rows)
-- Time: 39 413,285 ms


-- bottom line: if we need to update stats for 4+ suites, doing all suites at
-- once is faster
