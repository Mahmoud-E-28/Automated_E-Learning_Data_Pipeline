{{ config(materialized='table') }}

WITH base_instructors AS (
    SELECT DISTINCT 
        COALESCE(instructor, 'Unknown Instructor') AS instructor_name
    FROM {{ ref('int_courses_standardized') }}
    WHERE instructor IS NOT NULL
),

ranked_instructors AS (
    SELECT 
        -- بنبدا الترقيم من 1 للمدرسين المعروفين
        ROW_NUMBER() OVER(ORDER BY instructor_name) AS instructor_id,
        instructor_name
    FROM base_instructors
    WHERE instructor_name != 'Unknown Instructor'
)

-- دمج المعروفين مع الـ Unknown برقم ثابت -1
SELECT instructor_id, instructor_name FROM ranked_instructors
UNION ALL
SELECT -1, 'Unknown Instructor'