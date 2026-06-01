-- Example 1: SELECT * with ORDER BY without LIMIT and COUNT(DISTINCT)
-- Triggers: SELECT_STAR, ORDER_BY_WITHOUT_LIMIT, COUNT_DISTINCT, PARTITION_FILTER
SELECT *, COUNT(DISTINCT user_id) AS unique_users
FROM `project.dataset.user_events`
ORDER BY created_at;


-- Example 2: NULL comparison and LIKE leading wildcard
-- Triggers: NULL_COMPARISON, LIKE_LEADING_WILDCARD
SELECT user_id, email, status
FROM `project.dataset.users`
WHERE deleted_at = NULL
  AND email LIKE '%@example.com';


-- Example 3: CROSS JOIN and scalar subquery in SELECT
-- Triggers: CROSS_JOIN, SCALAR_SUBQUERY_IN_SELECT
SELECT
  u.id,
  u.name,
  (SELECT MAX(score) FROM `project.dataset.scores` s WHERE s.user_id = u.id) AS max_score
FROM `project.dataset.users` u
CROSS JOIN `project.dataset.regions` r;


-- Example 4: Repeated subquery and UNNECESSARY_DISTINCT with GROUP BY
-- Triggers: REPEATED_SUBQUERY, UNNECESSARY_DISTINCT
SELECT DISTINCT
  sub.user_id,
  sub.total_events
FROM (
  SELECT user_id, COUNT(*) AS total_events
  FROM `project.dataset.events`
  WHERE event_date >= '2024-01-01'
  GROUP BY user_id
) sub
JOIN (
  SELECT user_id, COUNT(*) AS total_events
  FROM `project.dataset.events`
  WHERE event_date >= '2024-01-01'
  GROUP BY user_id
) sub2 ON sub.user_id = sub2.user_id
GROUP BY sub.user_id, sub.total_events;
