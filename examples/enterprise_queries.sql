-- Enterprise optimization examples (v0.2 rules).
-- Run against examples/sample_metadata.json to activate metadata-aware rules:
--   bq-optimizer --file examples/enterprise_queries.sql --metadata examples/sample_metadata.json

-- Example 1: Full-table DELETE -> recommend TRUNCATE
-- Triggers: TRUNCATE_DML
DELETE FROM `project.dataset.orders`;


-- Example 2: INSERT then UPDATE same target in a session -> recommend MERGE,
-- and the target is updated twice -> REDUNDANT_UPDATES
-- Triggers: MERGE_OPTIMIZATION, REDUNDANT_UPDATES
INSERT INTO `project.dataset.users` (user_key, email)
SELECT user_key, email FROM `project.dataset.staging_users`;
UPDATE `project.dataset.users` SET email = LOWER(email) WHERE email IS NOT NULL;
UPDATE `project.dataset.users` SET country = 'US' WHERE country IS NULL;


-- Example 3: External table joined, STRING join key, suboptimal order, self-scan
-- Triggers: NATIVE_CONVERSION, SUBOPTIMAL_JOIN_KEYS, JOIN_ORDERING, REDUNDANT_SCANS
SELECT u.user_key, o.order_id, x.rate
FROM `project.dataset.users` u
JOIN `project.dataset.orders` o ON u.user_key = o.user_key
JOIN `project.dataset.exchange_rates_ext` x ON x.currency = 'USD'
JOIN `project.dataset.users` u2 ON u2.user_key = u.user_key;


-- Example 4: CREATE TABLE AS SELECT * -> recommend a clone
-- Triggers: TABLE_CLONING
CREATE TABLE `project.dataset.orders_backup` AS
SELECT * FROM `project.dataset.orders`;


-- Example 5: EXCEPT DISTINCT over partitioned tables without a partition filter
-- Triggers: UNFILTERED_PARTITION
SELECT * FROM `project.dataset.orders`
EXCEPT DISTINCT
SELECT * FROM `project.dataset.orders_backup`;


-- Example 6: case-insensitive comparison via UPPER(), and a huge IN list
-- Triggers: STRING_COMPARISON, LARGE_IN_CLAUSE
SELECT user_key
FROM `project.dataset.users`
WHERE UPPER(country) = 'US'
  AND user_key IN ('k1','k2','k3','k4','k5','k6','k7','k8','k9','k10',
                   'k11','k12','k13','k14','k15','k16','k17','k18','k19','k20',
                   'k21','k22','k23','k24','k25','k26','k27','k28','k29','k30',
                   'k31','k32','k33','k34','k35','k36','k37','k38','k39','k40',
                   'k41','k42','k43','k44','k45','k46','k47','k48','k49','k50','k51');
