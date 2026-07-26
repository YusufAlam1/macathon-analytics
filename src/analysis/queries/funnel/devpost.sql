-- ============================================================
-- REBUILD devpost_people  (view  ->  real table, email = PK)
-- ============================================================
-- Data model (one row per PERSON, a person belongs to exactly one project):
--     Project Title | first_name | last_name | email(PK)
--
-- Source `devpost` is one row per PROJECT with up to 4 member slots
-- (first_name_1..4 / last_name_1..4 / email_1..4). We unpivot the 4 slots,
-- drop empty slots, lowercase/trim the email, and enforce one-project-per-person.
--
-- AUDIT — why dedup is needed:
--   4 people appear on 2 projects each because they created a throwaway
--   Draft in addition to their real Submitted project. We keep the real one:
--     Gagan Bhattarai   Untitled(Draft)  -> thru.ai(Submitted)
--     Jason Medeiros    mistake(Draft)   -> CivicSense(Submitted)
--     Anasthecode       Untitled(Draft)  -> SynapseStream(Submitted)
--     Uddrity Das       Untitled(Draft)  -> BridgeCare(Submitted)
--   Tiebreaker: prefer Project Status 'Submitted%', then Highest Step 'Submit',
--   then project title. 189 raw slots -> 185 distinct people.
-- ============================================================

-- DROP VIEW IF EXISTS devpost_people;
-- DROP TABLE IF EXISTS devpost_people;

-- CREATE TABLE devpost_people (
--     "Project Title" TEXT,
--     first_name      TEXT,
--     last_name       TEXT,
--     email           TEXT PRIMARY KEY
-- );

-- INSERT INTO devpost_people ("Project Title", first_name, last_name, email)

WITH people AS (
    SELECT "Project Title" AS project_title,
           TRIM(first_name_1) AS first_name, TRIM(last_name_1) AS last_name,
           LOWER(TRIM(email_1)) AS email,
           "Project Status" AS status, "Highest Step Completed" AS step
    FROM devpost
    UNION ALL
    SELECT "Project Title", TRIM(first_name_2), TRIM(last_name_2),
           LOWER(TRIM(email_2)), "Project Status", "Highest Step Completed"
    FROM devpost
    UNION ALL
    SELECT "Project Title", TRIM(first_name_3), TRIM(last_name_3),
           LOWER(TRIM(email_3)), "Project Status", "Highest Step Completed"
    FROM devpost
    UNION ALL
    SELECT "Project Title", TRIM(first_name_4), TRIM(last_name_4),
           LOWER(TRIM(email_4)), "Project Status", "Highest Step Completed"
    FROM devpost
),
-- drop empty member slots (short teams leave slots 2-4 blank)
filtered AS (
    SELECT * FROM people
    WHERE first_name <> '' AND email <> ''
),
-- one row per email: prefer the real (Submitted) project over a throwaway Draft
ranked AS (
    SELECT *,
        ROW_NUMBER() OVER (
            PARTITION BY email
            ORDER BY CASE WHEN status LIKE 'Submitted%' THEN 0 ELSE 1 END,
                     CASE WHEN step = 'Submit'          THEN 0 ELSE 1 END,
                     project_title
        ) AS rn
    FROM filtered
)
SELECT project_title, first_name, last_name, email
FROM ranked
WHERE rn = 1
ORDER BY project_title, first_name;


-- ============================================================
-- Verification (run after the rebuild)
-- ============================================================

-- Row count — expect 185 distinct people
SELECT COUNT(*) AS people_count, COUNT(DISTINCT email) AS distinct_emails
FROM devpost_people;

-- No email should appear twice (PK guarantees this; sanity check anyway)
SELECT email, COUNT(*) AS n
FROM devpost_people
GROUP BY email
HAVING COUNT(*) > 1;

-- Projects with their team sizes
SELECT "Project Title", COUNT(*) AS team_size
FROM devpost_people
GROUP BY "Project Title"
ORDER BY team_size DESC, "Project Title";