{{ config(materialized='table') }}

WITH distinct_domains AS (
    SELECT DISTINCT domain_name
    FROM {{ ref('int_courses_standardized') }}
    WHERE domain_name IS NOT NULL
)

SELECT 
    ROW_NUMBER() OVER(ORDER BY domain_name) AS domain_id,
    domain_name
FROM distinct_domains

UNION ALL

-- إضافة صف للقيم المجهولة عشان الـ Left Join في الـ Fact Table
SELECT -1, 'Unknown'