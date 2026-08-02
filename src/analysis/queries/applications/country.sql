-- Demographic distribution by country/continent bucket
WITH
    mapped AS (
        SELECT
            CASE
                WHEN LOWER("Country of Residence") = 'canada' THEN 'Canada'
                -- WHEN LOWER("Country of Residence") = 'india' THEN 'India'
                -- WHEN LOWER("Country of Residence") IN ('united states of america', 'usa', 'us') THEN 'United States of America'
                -- WHEN LOWER("Country of Residence") IN (
                --     'pakistan',
                --     'paksitan',
                --     'india',
                --     'nepal',
                --     'uzbekistan',
                --     'united arab emirates',
                --     'turkiye',
                --     'saudi arabia',
                --     'qatar',
                --     'philippines',
                --     'malaysia',
                --     'iran',
                --     'indonesia',
                --     'bangladesh',
                --     'viet nam',
                --     'vietnam'
                -- ) THEN 'Asia'
                -- WHEN LOWER("Country of Residence") IN (
                --     'nigeria',
                --     'tunisia',
                --     'south africa',
                --     'rwanda',
                --     'kenya',
                --     'egypt'
                -- ) THEN 'Africa'
                -- WHEN LOWER("Country of Residence") IN ('north macedonia', 'germany') THEN 'Europe'
                -- WHEN LOWER("Country of Residence") IN (
                --     'mexico',
                --     'brazil',
                --     'brasil',
                --     'peru',
                --     'costa rica'
                -- ) THEN 'South America'
                -- ELSE 'Other'
                ELSE 'International'
            END AS "Country of Residence"
        FROM
            applications_wide
    )
SELECT
    "Country of Residence",
    CASE "Country of Residence"
        WHEN 'Canada' THEN 1
        WHEN 'India' THEN 2
        WHEN 'United States' THEN 3
        WHEN 'Asia' THEN 4
        WHEN 'Africa' THEN 5
        WHEN 'South America' THEN 6
        WHEN 'Europe' THEN 7
        ELSE 8
    END AS sort_order,
    COUNT(*) AS country_count
FROM
    mapped
GROUP BY
    "Country of Residence"
ORDER BY
    sort_order ASC;