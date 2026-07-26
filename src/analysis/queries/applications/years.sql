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
                AND "This hackathon is open to students only. What is your level of study?" LIKE 'Undergraduate%' THEN 'Student+'
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
        WHEN 'Student+' THEN 6
        WHEN 'Post-Graduate' THEN 7
        ELSE 8
    END AS sort_order,
    COUNT(*) AS count
FROM
    clean
GROUP BY
    category
ORDER BY
    sort_order ASC;