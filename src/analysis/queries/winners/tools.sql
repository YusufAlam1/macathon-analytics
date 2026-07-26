
SELECT * FROM devpost;



SELECT "Which Mac A Thon Prize Category Will Your Team Be Submitting For?"
    , COUNT(*) AS count
FROM devpost
GROUP BY "Which Mac A Thon Prize Category Will Your Team Be Submitting For?";

SELECT DISTINCT "Built With"
FROM devpost;


SELECT "name"
FROM PRAGMA_TABLE_INFO('devpost');

SELECT DISTINCT "Opt-In Prizes"
FROM devpost;


SELECT DISTINCT "Which Of The Following Ai Tools Did You Use This Weekend?"
FROM devpost;

SELECT 
    SUM(CASE WHEN "Which Of The Following Ai Tools Did You Use This Weekend?" LIKE '%OpenAI%' THEN 1 ELSE 0 END) AS gpt_count,
    SUM(CASE WHEN "Which Of The Following Ai Tools Did You Use This Weekend?" LIKE '%Anthropic%' THEN 1 ELSE 0 END) AS claude_count,
    SUM(CASE WHEN "Which Of The Following Ai Tools Did You Use This Weekend?" LIKE '%Gemini%' THEN 1 ELSE 0 END) AS gemini_count,
    SUM(CASE WHEN "Which Of The Following Ai Tools Did You Use This Weekend?" LIKE '%Gemma%' THEN 1 ELSE 0 END) AS gemma_count,
    SUM(CASE WHEN "Which Of The Following Ai Tools Did You Use This Weekend?" LIKE '%Hugging Face%' THEN 1 ELSE 0 END) AS hugging_face_count,
    SUM(CASE WHEN "Which Of The Following Ai Tools Did You Use This Weekend?" LIKE '%OpenRouter%' THEN 1 ELSE 0 END) AS openrouter_count,
    SUM(CASE WHEN "Which Of The Following Ai Tools Did You Use This Weekend?" LIKE '%ElevenLabs%' THEN 1 ELSE 0 END) AS elevenlabs_count
    -- SUM(CASE WHEN "Which Of The Following Ai Tools Did You Use This Weekend?" LIKE ''
    -- SUM(CASE WHEN "Which Of The Following Ai Tools Did You Use This Weekend?" LIKE '%OpenAI%' THEN 1 ELSE 0 END) AS gpt_count
FROM devpost;