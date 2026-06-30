{{ config(materialized='table') }}

WITH base_languages AS (
    SELECT DISTINCT 
        COALESCE(language, 'Unknown Language') AS language_name
    FROM {{ ref('int_courses_standardized') }}
    WHERE language IS NOT NULL
),

ranked_languages AS (
    SELECT 
        ROW_NUMBER() OVER(ORDER BY language_name) AS language_id,
        language_name
    FROM base_languages
    WHERE language_name <> 'Unknown Language'
)

SELECT language_id, language_name FROM ranked_languages
UNION ALL
SELECT -1, 'Unknown Language'