-- Returning hackers: were they at Mac-a-Thon last time (Jan. 2025)?
SELECT
    "Were you a hacker at Mac-a-Thon last time (Jan. 2025)?" AS attended_last_year,
    COUNT(*) AS count
FROM
    applications_wide
WHERE
    "Were you a hacker at Mac-a-Thon last time (Jan. 2025)?" IS NOT NULL
GROUP BY
    attended_last_year
    -- Yes before No
ORDER BY
    attended_last_year DESC;