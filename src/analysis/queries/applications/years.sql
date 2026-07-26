-- Demographic distribution by academic year category
WITH
    clean AS (
        SELECT
            *,
            CASE
                WHEN "This hackathon is open to students only. What is your level of study?" = 'Secondary/High School' THEN 'Highschool'
                WHEN "This hackathon is open to students only. What is your level of study?" LIKE 'Grad%'
                OR "This hackathon is open to students only. What is your level of study?" LIKE '%grad %'
                OR "This hackathon is open to students only. What is your level of study?" LIKE 'Master%'
                OR "This hackathon is open to students only. What is your level of study?" LIKE '%lenovo%' THEN 'Post-Graduate'
                WHEN "Age (ex. 20)" LIKE '18%'
                OR "Age (ex. 20)" = 17 THEN 'Freshman'
                WHEN "Age (ex. 20)" = 19 THEN 'Sophomore'
                WHEN "Age (ex. 20)" = 20 THEN 'Junior'
                WHEN "Age (ex. 20)" BETWEEN 21 AND 22 THEN 'Senior'
                WHEN "Age (ex. 20)" >= 23
                AND "This hackathon is open to students only. What is your level of study?" LIKE 'Undergraduate%' THEN 'Too Old'
                ELSE 'Other'
            END AS category
        FROM
            applications_wide
    )
SELECT
    category,
    CASE category
        WHEN 'Highschool' THEN 1
        WHEN 'Freshman' THEN 2
        WHEN 'Sophomore' THEN 3
        WHEN 'Junior' THEN 4
        WHEN 'Senior' THEN 5
        WHEN 'Senior (co-op)' THEN 6
        WHEN 'Post- Graduate' THEN 7
        WHEN 'Too Old' THEN 8
        ELSE 9
    END AS sort_order,
    COUNT(*) AS count
FROM
    clean
GROUP BY
    category
ORDER BY
    sort_order ASC;






-- Counting age buckets per level of study / year of study
-- *Caveat we almost fully accepted undergrads
-- SELECT
--     -- CONCAT(a."First Name", ' ', a."Last Name(s)") AS hacker,
--     -- a."Email Address" AS applicant_email,
--     -- r.Email AS gdg_attendees_email,
--     "This hackathon is open to students only. What is your level of study?" AS level_of_study,
--     a."Age (ex. 20)" AS age,
--     r."Year of study (if applicable)" AS year_of_study,
--     COUNT(*) AS count
-- FROM
--     applications a
--     JOIN gdg_attendees r ON a."Email Address" = r.Email
--     OR a."Preferred Email" = r.Email
--     OR "McMaster Email (if you are a McMaster student)" = r.Email
--     OR CONCAT (a."First Name", ' ', a."Last Name(s)") = CONCAT (r."First Name", ' ', r."Last Name")
-- GROUP BY
--     age,
--     year_of_study
-- ORDER BY
--     year_of_study DESC,
--     age DESC;







-- SELECT
--     COUNT(*)
-- FROM
--     applications
-- WHERE 1 = 1 AND (
--         "This hackathon is open to students only. What is your level of study?" IN ('Secondary/High School')
--         OR "This hackathon is open to students only. What is your level of study?" LIKE '%Undergraduate%'
--         OR "This hackathon is open to students only. What is your level of study?" LIKE '%Graduate%'
--     )
--     AND "Accepted" = 'Y';

-- SELECT
--     -- AVG("Age (ex. 20)") AS average_age
--     "Age (ex. 20)" AS age,
--     COUNT("Age (ex. 20)") AS count
-- FROM
--     applications
-- WHERE
--     "This hackathon is open to students only. What is your level of study?" IN ('Secondary/High School')
-- GROUP BY
--     "Age (ex. 20)"
-- ORDER BY
--     age DESC;





-- -- SELECT AVG("Age (ex. 20)") AS average_age
-- -- FROM applications
-- -- WHERE "This hackathon is open to students only. What is your level of study?" LIKE '%Undergraduate%';
-- -- what level of study are people who are under 18 in?
-- SELECT
--     "This hackathon is open to students only. What is your level of study?" AS level_of_study,
--     "Age (ex. 20)" AS age
--     -- , COUNT("Age (ex. 20)") AS count
-- FROM
--     applications
--     -- WHERE "This hackathon is open to students only. What is your level of study?" LIKE '%High School%';
-- WHERE
--     age < 18;




-- SELECT 
--     "This hackathon is open to students only. What is your level of study?" AS level_of_study
--     , "Age (ex. 20)" AS age
-- FROM applications
-- WHERE "Age (ex. 20)" >= 23
-- ORDER BY level_of_study DESC
--     , age DESC;




--     SELECT DISTINCT "Age (ex. 20)"
--         , "This hackathon is open to students only. What is your level of study?" AS level_of_study
--     FROM applications
--     WHERE "Age (ex. 20)" >= 23;
--     -- AND level_of_study NOT LIKE 'Undergraduate%';