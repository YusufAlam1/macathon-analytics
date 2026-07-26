-- ============================================================
-- CHECK-IN / ATTENDANCE  —  the "who was actually there" stage
-- ============================================================
-- Sits between RSVP and Devpost in the funnel:
--     Applied -> Accepted -> RSVPed -> ATTENDED -> Submitted a Devpost
--
-- DEFINITION (decided):  attended = checked in (TRUE)  OR  in devpost_people.
--   Rationale: a check-in scan misses people (busy table, scanned under a
--   different email), whereas building a Devpost project proves presence. So
--   anyone in devpost_people was there even if never scanned. We count
--   participation/attendance, not just the raw scan.
--
-- CAVEAT (for future context): RSVP was *required* (it feeds MLH), yet 9
--   accepted attendees never RSVPed (walk-ins). So "attended" is NOT a strict
--   subset of RSVP — a process gap to tighten next event, not a data error.
--
-- Source: `checkin` table (cleaned from checkin.csv):
--   first_name, last_name, email, checked_in (1=TRUE scan, 0=not).
--   'waitlist pending' (Karim Badr) and blanks were normalised to 0; he was
--   accepted but not in rsvp/devpost and not recalled present -> not attended.
--   The 4 meal columns were ignored per request.
--
-- Matching rigor mirrors retention.sql: email (any of an applicant's 3) or
-- full name, and devpost emails come pre-remapped via devpost_people.
-- ============================================================


-- ============================================================
-- 1. HEADLINE — the attendance number(s)
-- ============================================================
-- attended = scanned-in people  +  devpost builders who were NOT scanned.
-- We can't UNION on email alone (a person may appear under different emails in
-- checkin vs devpost), so we dedupe by matching on email OR full name.
WITH ci AS (                                 -- everyone with a TRUE scan
    SELECT LOWER(TRIM(email)) AS em, LOWER(TRIM(first_name)) AS fn, LOWER(TRIM(last_name)) AS ln
    FROM checkin
    WHERE checked_in = 1
),
dp_extra AS (                                -- devpost builders not already in ci
    SELECT d.email
    FROM devpost_people d
    WHERE NOT EXISTS (
        SELECT 1 FROM ci
        WHERE (ci.em = LOWER(TRIM(d.email)) AND TRIM(d.email) <> '')
           OR (ci.fn = LOWER(TRIM(d.first_name)) AND ci.ln = LOWER(TRIM(d.last_name)))
    )
)
SELECT
    (SELECT COUNT(*) FROM checkin WHERE checked_in = 1)       AS checked_in_scan,   -- 208
    (SELECT COUNT(*) FROM devpost_people)                     AS devpost_people,    -- 185
    (SELECT COUNT(*) FROM dp_extra)                           AS devpost_not_scanned,-- 31
    (SELECT COUNT(*) FROM ci) + (SELECT COUNT(*) FROM dp_extra) AS attended_total;  -- 239


-- ============================================================
-- 2. RSVP SECOND OPINION — does RSVP corroborate check-in?
-- ------------------------------------------------------------
-- Of everyone who RSVPed, how many actually showed (checked in)?
-- Big no-show gap is expected for a free student event and is exactly why
-- RSVP overstates attendance.
-- ============================================================
WITH rsvp_status AS (
    SELECT
        -- 1 if this RSVP person has a TRUE scan (scalar subquery avoids the
        -- AND/OR precedence trap that EXISTS(... OR ... AND checked_in) hits)
        (SELECT COUNT(*) FROM checkin c
         WHERE c.checked_in = 1
           AND (
                (LOWER(TRIM(c.email)) = LOWER(TRIM(r."Email")) AND TRIM(c.email) <> '')
             OR (LOWER(TRIM(c.first_name)) = LOWER(TRIM(r."First Name"))
                 AND LOWER(TRIM(c.last_name)) = LOWER(TRIM(r."Last Name")))
           )
        ) AS checked_in,
        -- 1 if they built a devpost project
        (SELECT COUNT(*) FROM devpost_people d
         WHERE LOWER(TRIM(d.email)) = LOWER(TRIM(r."Email"))
            OR (LOWER(TRIM(d.first_name)) = LOWER(TRIM(r."First Name"))
                AND LOWER(TRIM(d.last_name)) = LOWER(TRIM(r."Last Name")))
        ) AS in_devpost
    FROM rsvp r
)
SELECT
    COUNT(*)                                                              AS total_rsvp,          -- 316
    SUM(CASE WHEN checked_in > 0 THEN 1 ELSE 0 END)                       AS rsvp_and_checkedin,  -- 200
    SUM(CASE WHEN checked_in > 0 OR in_devpost > 0 THEN 1 ELSE 0 END)     AS rsvp_and_attended,   -- 204
    SUM(CASE WHEN checked_in = 0 AND in_devpost = 0 THEN 1 ELSE 0 END)    AS rsvp_no_show         -- 112
FROM rsvp_status;


-- ============================================================
-- 3. INSPECTION — walk-ins: attended but never RSVPed
-- ------------------------------------------------------------
-- The 9 (+ edge cases) accept-but-didn't-RSVP people. Flag for the "everyone
-- should RSVP next time" process note.
-- ============================================================
SELECT c.first_name, c.last_name, c.email
FROM checkin c
WHERE c.checked_in = 1
  AND NOT EXISTS (
      SELECT 1 FROM rsvp r
      WHERE LOWER(TRIM(r."Email")) = LOWER(TRIM(c.email))
         OR (LOWER(TRIM(r."First Name")) = LOWER(TRIM(c.first_name))
             AND LOWER(TRIM(r."Last Name")) = LOWER(TRIM(c.last_name)))
  )
ORDER BY c.last_name, c.first_name;


-- ============================================================
-- 4. INSPECTION — built a Devpost project but not scanned in
-- ------------------------------------------------------------
-- These are the +people the union adds to the scan count (the "missed by the
-- check-in table but demonstrably present" group).
-- ============================================================
SELECT d."Project Title", d.first_name, d.last_name, d.email
FROM devpost_people d
WHERE NOT EXISTS (
    SELECT 1 FROM checkin c
    WHERE c.checked_in = 1
      AND ( (LOWER(TRIM(c.email)) = LOWER(TRIM(d.email)) AND TRIM(c.email) <> '')
          OR (LOWER(TRIM(c.first_name)) = LOWER(TRIM(d.first_name))
              AND LOWER(TRIM(c.last_name)) = LOWER(TRIM(d.last_name))) )
)
ORDER BY d."Project Title", d.first_name;
