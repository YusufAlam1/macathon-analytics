WITH
    counts AS (
        SELECT
            "How did you hear about us?",
            COUNT("How did you hear about us?") AS attribution_count
        FROM
            applications_wide
        GROUP BY
            "How did you hear about us?"
        ORDER BY
            attribution_count DESC
    )
SELECT
    CASE
        WHEN attribution_count > 5 THEN "How did you hear about us?"
        ELSE 'Other'
    END AS source,
    SUM(attribution_count) AS attribution_count
FROM
    counts
GROUP BY
    source
ORDER BY
    attribution_count DESC;