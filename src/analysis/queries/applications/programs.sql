-- Program distribution, undergraduate students only
WITH
    rename AS (
        SELECT
            "Which of the following best describes your program?" AS program,
            "This hackathon is open to students only. What is your level of study?" AS level_of_study
        FROM
            applications_wide
    ),
    clean AS (
        SELECT
            *,
            CASE
                WHEN level_of_study = 'Secondary/High School' THEN 'High School'
                WHEN program LIKE '%Computer Science%' THEN 'Software'
                WHEN program LIKE '%Engineering%' THEN 'Engineering'
                WHEN program LIKE 'Math%' THEN 'Math'
                WHEN program LIKE 'Business%' THEN 'Business'
                WHEN program LIKE '%Technology%' THEN 'Technology'
                ELSE 'Other'
            END AS program_type
        FROM
            rename
    )
SELECT
    *,
    CASE program_type
        WHEN 'Software' THEN 1
        WHEN 'Engineering' THEN 2
        WHEN 'Math' THEN 3
        WHEN 'Business' THEN 4
        WHEN 'Technology' THEN 5
        WHEN 'Other' THEN 6
        WHEN 'High School' THEN 7
        ELSE 8
    END AS sort_order,
    COUNT(program) AS program_count
FROM
    clean
GROUP BY
    program_type
ORDER BY
    sort_order;