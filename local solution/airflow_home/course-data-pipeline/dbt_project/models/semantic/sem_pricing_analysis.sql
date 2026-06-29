{{ config(materialized='table') }}

WITH source AS (
    SELECT * FROM {{ ref('int_courses_standardized') }}
),

pricing_by_category AS (
    SELECT
        price_category,
        COUNT(*) AS course_count,
        ROUND(AVG(rating), 2) AS avg_rating,
        ROUND(AVG(price), 2) AS avg_price,
        ROUND(MIN(price), 2) AS min_price,
        ROUND(MAX(price), 2) AS max_price,
        SUM(enrolled_students) AS total_enrolled,
        ROUND(AVG(enrolled_students), 0) AS avg_enrolled,
        ROUND(AVG(duration_hours), 1) AS avg_duration_hours,
        ROUND(AVG(cost_per_hour), 2) AS avg_cost_per_hour,
        ROUND(AVG(value_score), 2) AS avg_value_score,
        ROUND(AVG(engagement_rate_pct), 2) AS avg_engagement_pct,
        COUNT(CASE WHEN price_model = 'Subscription' THEN 1 END) AS subscription_count,
        COUNT(CASE WHEN price_model = 'One Time' THEN 1 END) AS one_time_count
    FROM source
    GROUP BY price_category
),

combined AS (
    SELECT
        pc.*,
        ROUND(pc.course_count * 100.0 / NULLIF(SUM(pc.course_count) OVER (), 0), 1) AS pct_of_total
    FROM pricing_by_category pc
)

SELECT * FROM combined
ORDER BY
    CASE price_category
        WHEN 'Free' THEN 1
        WHEN 'Cheap' THEN 2
        WHEN 'Medium' THEN 3
        WHEN 'Expensive' THEN 4
        WHEN 'Premium' THEN 5
        ELSE 6
    END
