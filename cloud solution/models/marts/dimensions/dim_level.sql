{{ config(materialized='table') }}

WITH base_levels AS (
    SELECT DISTINCT 
        COALESCE(level, 'Unknown') AS level_name
    FROM {{ ref('int_courses_standardized') }}
    WHERE level IS NOT NULL
),

ranked_levels AS (
    SELECT 
        ROW_NUMBER() OVER(ORDER BY level_name) AS level_id,
        level_name
    FROM base_levels
    WHERE level_name != 'Unknown'
)

-- دمج المستويات المعروفة مع الـ Unknown برقم ثابت -1
SELECT level_id, level_name FROM ranked_levels
UNION ALL
SELECT -1, 'Unknown'