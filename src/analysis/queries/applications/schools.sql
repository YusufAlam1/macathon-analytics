WITH
    rename AS (
        SELECT
            "Which school/college/university are you currently enrolled in? (If your school/institution is not in the list below, use this list to find a school/institution and paste it in 'Other')" AS school,
            "This hackathon is open to students only. What is your level of study?" AS level_of_study,
            "Country of Residence" AS country,
            "Age (ex. 20)" AS age
        FROM
            applications_wide
    ),
    school_mapping AS (
        SELECT
            CASE
                WHEN level_of_study = 'Secondary/High School' THEN 'High School'
                WHEN school LIKE '%McMaster%' THEN 'McMaster University'
                WHEN school LIKE '%University of Toronto%' THEN 'University of Toronto'
                WHEN school LIKE '%Waterloo%' THEN 'University of Waterloo'
                WHEN school LIKE '%laurier%' THEN 'Wilfrid Laurier University'
                WHEN school LIKE '%Western%' THEN 'Western University'
                WHEN school LIKE '%York%' THEN 'York University'
                WHEN school LIKE '%Ontario%Tech%' THEN 'Ontario Tech University'
                WHEN school LIKE '%Carleton%' THEN 'Carleton University'
                WHEN (
                    school LIKE '%college%'
                    OR school LIKE '%polytechnic%'
                )
                AND country = 'Canada' THEN 'College'
                ELSE school
            END AS school,
            country
        FROM
            rename
    ),
    school_counts AS (
        SELECT
            school,
            country,
            COUNT(*) AS count
        FROM
            school_mapping
        GROUP BY
            school,
            country
    ),
    grouped AS (
        SELECT
            CASE
                WHEN school IN ('High School', 'College') THEN school
                WHEN count < 20
                AND country = 'Canada' THEN 'Other Canada'
                WHEN count < 20
                AND country != 'Canada' THEN 'Other International'
                ELSE school
            END AS school_group,
            SUM(count) AS count
        FROM
            school_counts
        GROUP BY
            school_group
    )
SELECT
    school_group
    ,
    count,
    CASE school_group
        WHEN 'College' THEN 1
        WHEN 'High School' THEN 2
        WHEN 'Other Canada' THEN 3
        WHEN 'Other International' THEN 4
        ELSE 0
    END AS sort_order
FROM
    grouped
ORDER BY
    sort_order ASC,
    count DESC;

-- Extra Analysis Queries ONLY READ MAIN ONE AT THE TOP
--     -- Master list
-- SELECT DISTINCT
--     "Which school/college/university are you currently enrolled in? (If your school/institution is not in the list below, use this list to find a school/institution and paste it in 'Other')" AS school,
--     COUNT(*) AS count,
--     "Country of Residence" AS country,
--     "This hackathon is open to students only. What is your level of study?" AS level_of_study
-- FROM
--     applications
-- WHERE
--     level_of_study NOT LIKE '%High School%'
-- GROUP BY
--     school
-- ORDER BY
--     count DESC;
-- -- Name variation counts (For colleges)
-- SELECT DISTINCT
--     "Which school/college/university are you currently enrolled in? (If your school/institution is not in the list below, use this list to find a school/institution and paste it in 'Other')" AS school,
--     "Country of Residence",
--     COUNT(*) AS count
-- FROM
--     applications
-- WHERE
--     (
--         school LIKE '%college%'
--         OR school LIKE '%polytechnic%'
--     )
--     AND "Country of Residence" = 'Canada'
-- GROUP BY
--     school
-- ORDER BY
--     school;
-- SELECT DISTINCT
--     "This hackathon is open to students only. What is your level of study?" AS level_of_study,
--     "Which school/college/university are you currently enrolled in? (If your school/institution is not in the list below, use this list to find a school/institution and paste it in 'Other')" AS school,
--     COUNT(*) AS count
-- FROM
--     applications
-- GROUP BY
--     level_of_study,
--     school;
-- SELECT DISTINCT
--     "This hackathon is open to students only. What is your level of study?" AS level_of_study,
--     COUNT(*) AS count
-- FROM
--     applications
-- GROUP BY
--     level_of_study;



WITH schools_with_more_than_2_applicants AS (
        SELECT 
            "Which school/college/university are you currently enrolled in? (If your school/institution is not in the list below, use this list to find a school/institution and paste it in 'Other')",
        COUNT(*) AS count
    FROM applications_wide
    GROUP BY "Which school/college/university are you currently enrolled in? (If your school/institution is not in the list below, use this list to find a school/institution and paste it in 'Other')"
    HAVING COUNT(*) > 1
    ORDER BY count DESC
)
SELECT COUNT(*) AS school_count
FROM schools_with_more_than_2_applicants;