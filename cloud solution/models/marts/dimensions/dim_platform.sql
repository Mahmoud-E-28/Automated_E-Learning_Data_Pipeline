{{ config(materialized='table') }}

WITH base_platforms AS (
    SELECT DISTINCT 
        COALESCE(platform, 'Unknown') AS platform_name
    FROM {{ ref('int_courses_standardized') }}
    WHERE platform IS NOT NULL
),

ranked_platforms AS (
    SELECT 
        ROW_NUMBER() OVER(ORDER BY platform_name) AS platform_id,
        platform_name
    FROM base_platforms
    WHERE platform_name != 'Unknown'
)

-- دمج المنصات المعروفة مع الـ Unknown برقم ثابت -1
SELECT platform_id, platform_name FROM ranked_platforms
UNION ALL
SELECT -1, 'Unknown'