{{ config(materialized='table') }}

WITH base_types AS (
    SELECT DISTINCT 
        COALESCE(offering_type, 'Unknown') AS offering_type
    FROM {{ ref('int_courses_standardized') }}
    WHERE offering_type IS NOT NULL
),

ranked_types AS (
    SELECT 
        ROW_NUMBER() OVER(ORDER BY offering_type) AS offering_type_id,
        offering_type
    FROM base_types
    WHERE offering_type != 'Unknown'
)

-- دمج الأنواع المعروفة مع الـ Unknown برقم ثابت -1
SELECT offering_type_id, offering_type FROM ranked_types
UNION ALL
SELECT -1, 'Unknown'