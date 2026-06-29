{{ config(materialized='table') }}

WITH source AS (
    SELECT * FROM {{ ref('int_courses_standardized') }}
),

platform_stats AS (
    SELECT
        platform,
        COUNT(*) AS total_courses,
        ROUND(AVG(rating), 2) AS avg_rating,
        ROUND(MEDIAN(rating), 2) AS median_rating,
        SUM(enrolled_students) AS total_enrolled,
        ROUND(AVG(enrolled_students), 0) AS avg_enrolled_per_course,
        ROUND(AVG(price), 2) AS avg_price,
        ROUND(MEDIAN(price), 2) AS median_price,
        ROUND(AVG(duration_hours), 1) AS avg_duration_hours,
        ROUND(AVG(review_count), 0) AS avg_reviews,
        ROUND(AVG(engagement_rate_pct), 2) AS avg_engagement_pct,
        ROUND(AVG(value_score), 2) AS avg_value_score,
        ROUND(AVG(weighted_rating), 2) AS avg_weighted_rating,
        ROUND(AVG(cost_per_hour), 2) AS avg_cost_per_hour,
        COUNT(CASE WHEN price = 0 OR price IS NULL THEN 1 END) AS free_courses,
        COUNT(CASE WHEN rating >= 4.5 THEN 1 END) AS high_rated_courses,
        ROUND(
            COUNT(CASE WHEN rating >= 4.5 THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0),
            1
        ) AS pct_high_rated
    FROM source
    GROUP BY platform
)

SELECT * FROM platform_stats
