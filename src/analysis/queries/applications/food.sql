SELECT "name"
FROM PRAGMA_TABLE_INFO('gdg_attendees');

SELECT "Do you have any dietary restrictions?"
    , COUNT(*) AS count
FROM gdg_attendees
GROUP BY "Do you have any dietary restrictions?"
ORDER BY count DESC;