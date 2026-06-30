{{ config(materialized='table') }}

WITH dates AS (

    SELECT DISTINCT
        -- استخدام CONVERT للتحويل لـ YYYYMMDD
        CAST(CONVERT(VARCHAR(8), last_updated, 112) AS INTEGER) AS date_id,
        
        last_updated AS full_date,
        
        -- استخدام DATEPART لاستخراج أجزاء التاريخ
        DATEPART(day, last_updated) AS day,
        DATEPART(month, last_updated) AS month,
        DATEPART(quarter, last_updated) AS quarter,
        DATEPART(year, last_updated) AS year

    FROM {{ ref('int_courses_standardized') }}
    WHERE last_updated IS NOT NULL

),

unknown_date AS (

    SELECT
        -1 AS date_id,
        NULL AS full_date,
        NULL AS day,
        NULL AS month,
        NULL AS quarter,
        NULL AS year

)

SELECT * FROM dates
UNION ALL
SELECT * FROM unknown_date