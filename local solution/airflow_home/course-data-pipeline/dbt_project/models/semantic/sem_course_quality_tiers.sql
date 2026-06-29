{{ config(materialized='table') }}

WITH source AS (
    SELECT * FROM {{ ref('int_courses_standardized') }}
),

tiered AS (
    SELECT
        *,
        CASE
            WHEN rating IS NULL THEN 'Unrated'
            WHEN rating >= 4.5 AND enrolled_students >= 1000 AND engagement_rate_pct >= 1.0
                THEN 'Premium'
            WHEN rating >= 4.0 AND enrolled_students >= 500
                THEN 'High'
            WHEN rating >= 3.0
                THEN 'Medium'
            ELSE 'Low'
        END AS quality_tier
    FROM source
),

tier_summary AS (
    SELECT
        quality_tier,
        platform,
        domain_name,
        COUNT(*) AS course_count,
        ROUND(AVG(rating), 2) AS avg_rating,
        ROUND(AVG(price), 2) AS avg_price,
        SUM(enrolled_students) AS total_enrolled,
        ROUND(AVG(engagement_rate_pct), 2) AS avg_engagement_pct,
        ROUND(AVG(value_score), 2) AS avg_value_score,
        ROUND(AVG(duration_hours), 1) AS avg_duration_hours,
        ROUND(AVG(cost_per_hour), 2) AS avg_cost_per_hour
    FROM tiered
    GROUP BY quality_tier, platform, domain_name
)

SELECT
    *,
    ROUND(
        course_count * 100.0 / NULLIF(SUM(course_count) OVER (PARTITION BY platform), 0),
        1
    ) AS pct_of_platform
FROM tier_summary
ORDER BY
    platform,
    CASE quality_tier
        WHEN 'Premium' THEN 1
        WHEN 'High' THEN 2
        WHEN 'Medium' THEN 3
        WHEN 'Low' THEN 4
        ELSE 5
    END,
    total_enrolled DESC
