-- Prior hackathon experience distribution
SELECT
    "How many hackathons have you attended in the past?" AS experience,
    COUNT(*) AS count,
    CASE "How many hackathons have you attended in the past?"
        WHEN 'None' THEN 0
        WHEN '1' THEN 1
        WHEN '2 - 3' THEN 2
        WHEN '4+' THEN 3
        ELSE 9
    END AS sort_order
FROM applications_wide
WHERE "How many hackathons have you attended in the past?" IS NOT NULL
GROUP BY experience
ORDER BY sort_order ASC;
