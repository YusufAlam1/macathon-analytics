-- Gender distribution — CANONICAL SPEC for the dashboard's gender split bar.
-- Mirrored in pandas by filtered/aggregations.py gender_counts() and the
-- GENDER_* constants in filtered/loaders.py — keep them in lockstep.
--
-- COVERAGE CAVEAT: gdg_gender is joined in from gdg_attendees, which only
-- contains people who reached the RSVP stage. So the column is non-null for
-- exactly the RSVPed population and NULL for everyone who never RSVPed. It is
-- a coverage gap, not missing data to impute — which is why the dashboard
-- gates the gender chart and the gender filter on the funnel stage rather than
-- charting a column that is NULL for 63% of applicants.


-- Coverage check: confirms the NULLs are exactly the non-RSVPed applicants.
-- Expected: rsvped rows have 0 nulls; non-rsvped rows are 100% null.
SELECT
    is_rsvped,
    COUNT(*)                                          AS applicants,
    SUM(CASE WHEN gdg_gender IS NULL THEN 1 ELSE 0 END) AS null_gender
FROM applications_wide
GROUP BY is_rsvped;


-- The chart's aggregation: the two-category split over the covered
-- (RSVPed) population. NULLs are dropped, never bucketed into a third
-- category the survey never collected.
SELECT
    gdg_gender AS gender,
    COUNT(*)   AS count
FROM applications_wide
WHERE gdg_gender IS NOT NULL
GROUP BY gdg_gender
ORDER BY count DESC;


-- Same split at each deeper funnel stage — each is a subset of RSVPed, so
-- every one of them has full gender coverage (this is why any stage at or
-- past RSVPed unlocks the filter in the dashboard).
SELECT
    gdg_gender                AS gender,
    SUM(is_rsvped)            AS rsvped,
    SUM(is_attended)          AS attended,
    SUM(is_completed)         AS completed_project
FROM applications_wide
WHERE gdg_gender IS NOT NULL
GROUP BY gdg_gender;


-- Raw source of truth, pre-join: the RSVP survey's own gender question.
-- The counts here should match the second query above.
SELECT "What gender best describes you?" AS gender,
    COUNT(*) AS count
FROM gdg_attendees
GROUP BY "What gender best describes you?";
