SELECT LENGTH("Answer this short answer question in 5 sentences or less: Tell us about yourself, and why you would like to attend the Mac-a-Thon.") AS "about_length"
FROM applications_wide
ORDER BY "about_length" ASC;
--
SELECT LENGTH("Answer this short answer question in 5 sentences or less: What is a project that you recently worked on? This does not have to be related to computer science or software.") AS "project_length"
FROM applications_wide
ORDER BY "project_length" ASC;
--
SELECT (LENGTH("Answer this short answer question in 5 sentences or less: Tell us about yourself, and why you would like to attend the Mac-a-Thon.") +
    LENGTH("Answer this short answer question in 5 sentences or less: What is a project that you recently worked on? This does not have to be related to computer science or software.")) AS "response_length"
FROM applications_wide
ORDER BY "response_length" ASC;