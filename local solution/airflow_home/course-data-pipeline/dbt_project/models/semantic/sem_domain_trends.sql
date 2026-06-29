{{ config(materialized='table') }}

WITH source AS (
    SELECT * FROM {{ ref('int_courses_standardized') }}
),

domain_stats AS (
    SELECT
        domain_name,
        COUNT(*) AS total_courses,
        COUNT(DISTINCT platform) AS platforms_offering,
        ROUND(AVG(rating), 2) AS avg_rating,
        SUM(enrolled_students) AS total_enrolled,
        ROUND(AVG(price), 2) AS avg_price,
        ROUND(AVG(duration_hours), 1) AS avg_duration_hours,
        ROUND(AVG(engagement_rate_pct), 2) AS avg_engagement_pct,
        ROUND(AVG(value_score), 2) AS avg_value_score,
        MODE(level) AS most_common_level,
        MODE(price_category) AS most_common_price_category,
        COUNT(CASE WHEN rating >= 4.0 THEN 1 END) AS courses_rated_4_plus,
        ROUND(
            COUNT(CASE WHEN rating >= 4.0 THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0),
            1
        ) AS pct_rated_4_plus
    FROM source
    GROUP BY domain_name
)

SELECT * FROM domain_stats
ORDER BY total_enrolled DESC
