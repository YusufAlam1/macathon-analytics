-- ============================================================
-- FUNNEL COUNTS (dashboard) — tidy, one row per stage
-- ------------------------------------------------------------
-- Applied → Accepted → RSVPed → Attended → Completed Project
--
-- This is the chart-facing query. The matching logic (email/name joins,
-- devpost remaps, attended = door-scan OR built-a-project) is the SAME as
-- retention.sql Section 5 — kept here standalone so the dashboard can load
-- one file that returns a stage/count table ready for a funnel chart.
-- See retention.sql for the full rationale, audits, and inspection views.
--
-- NOTE: the devpost→application email reconciliation mapping (participant
-- names + personal emails = PII) lives in the private `devpost_remap` TABLE,
-- NOT inline here — this file is committed to the public repo. Build that
-- table locally with src/scripts/build_devpost_remap.py (gitignored), and it
-- ships to the deployed app via the Turso database (never via the repo).
-- ============================================================
WITH devpost_people_clean AS (
    SELECT dp."Project Title" AS project_title,
           LOWER(TRIM(dp.first_name)) AS first_name,
           LOWER(TRIM(dp.last_name))  AS last_name,
           LOWER(TRIM(COALESCE(rm.app_email, dp.email))) AS email
    FROM devpost_people dp
    LEFT JOIN devpost_remap rm ON LOWER(TRIM(dp.email)) = rm.devpost_email
    WHERE TRIM(dp.first_name) <> '' AND TRIM(dp.email) <> ''
),
funnel AS (
    SELECT
        a."Email Address" AS applied_email,
        CASE WHEN a."Accepted" = 'Y' THEN a."Email Address" END AS accepted_email,
        (
            SELECT g."Email" FROM gdg_attendees g
            WHERE LOWER(TRIM(g."Email")) = LOWER(TRIM(a."Email Address"))
               OR LOWER(TRIM(g."Email")) = LOWER(TRIM(a."Preferred Email"))
               OR LOWER(TRIM(g."Email")) = LOWER(TRIM(a."McMaster Email (if you are a McMaster student)"))
               OR LOWER(TRIM(g."Your preferred email address (we will use this email to reach out to you about this event)")) = LOWER(TRIM(a."Email Address"))
               OR LOWER(TRIM(g."Your preferred email address (we will use this email to reach out to you about this event)")) = LOWER(TRIM(a."Preferred Email"))
               OR LOWER(TRIM(g."Your preferred email address (we will use this email to reach out to you about this event)")) = LOWER(TRIM(a."McMaster Email (if you are a McMaster student)"))
               OR LOWER(TRIM(g."First name" || ' ' || g."Last Name"))
                  = LOWER(TRIM(a."First Name" || ' ' || a."Last Name(s)"))
            LIMIT 1
        ) AS rsvped_email,
        (
            SELECT 1 WHERE
               EXISTS (
                   SELECT 1 FROM checkin c
                   WHERE c.checked_in = 1
                     AND ( LOWER(TRIM(c.email)) = LOWER(TRIM(a."Email Address"))
                        OR LOWER(TRIM(c.email)) = LOWER(TRIM(a."Preferred Email"))
                        OR LOWER(TRIM(c.email)) = LOWER(TRIM(a."McMaster Email (if you are a McMaster student)"))
                        OR LOWER(TRIM(c.first_name || ' ' || c.last_name))
                           = LOWER(TRIM(a."First Name" || ' ' || a."Last Name(s)")) )
               )
               OR EXISTS (
                   SELECT 1 FROM devpost_people_clean d
                   WHERE d.email = LOWER(TRIM(a."Email Address"))
                      OR d.email = LOWER(TRIM(a."Preferred Email"))
                      OR d.email = LOWER(TRIM(a."McMaster Email (if you are a McMaster student)"))
                      OR (d.first_name || ' ' || d.last_name)
                         = LOWER(TRIM(a."First Name" || ' ' || a."Last Name(s)"))
               )
        ) AS attended_flag,
        (
            SELECT d.email FROM devpost_people_clean d
            WHERE d.email = LOWER(TRIM(a."Email Address"))
               OR d.email = LOWER(TRIM(a."Preferred Email"))
               OR d.email = LOWER(TRIM(a."McMaster Email (if you are a McMaster student)"))
               OR (d.first_name || ' ' || d.last_name)
                  = LOWER(TRIM(a."First Name" || ' ' || a."Last Name(s)"))
            LIMIT 1
        ) AS devpost_email
    FROM applications a
),
counts AS (
    SELECT
        COUNT(*)              AS applied,
        COUNT(accepted_email) AS accepted,
        COUNT(rsvped_email)   AS rsvped,
        COUNT(attended_flag)  AS attended,
        COUNT(devpost_email)  AS completed
    FROM funnel
)
-- Long format: one row per stage, ordered top-of-funnel first.
SELECT 'Applied'           AS stage, applied   AS count, 0 AS sort_order FROM counts
UNION ALL
SELECT 'Accepted',           accepted,  1 FROM counts
UNION ALL
SELECT 'RSVPed',             rsvped,    2 FROM counts
UNION ALL
SELECT 'Attended',           attended,  3 FROM counts
UNION ALL
SELECT 'Completed Project',  completed, 4 FROM counts
ORDER BY sort_order;
