WITH programs AS (
    SELECT "Which of the following best describes your program?" AS program,
        "Accepted",
        SUM(CASE WHEN "Accepted" = 'Y' THEN 1 ELSE 0 END) AS accepted_count,
        SUM(CASE WHEN "Accepted" = 'N' THEN 1 ELSE 0 END) AS rejected_count,
        COUNT(*) AS program_count
    FROM applications
    WHERE program != 'Secondary/High School'
    GROUP BY "Which of the following best describes your program?"
),
categorized_programs AS (
    SELECT
        *, 
        CASE
        WHEN
            program LIKE '%scienc%' OR
            program LIKE '%tech%' OR
            program LIKE '%engineer%' OR
            program LIKE '%math%'
        THEN 'STEM'
        ELSE 'NON-STEM'
        END AS program_type
    FROM programs
)
SELECT 
    program_type,
    SUM(accepted_count) AS acceptence_count,
    SUM(rejected_count) AS rejection_count,
    SUM(program_count) AS total_count
FROM categorized_programs
GROUP BY program_type;

-- SELECT * FROM categorized_programs
-- ORDER BY program_count DESC, program_type;