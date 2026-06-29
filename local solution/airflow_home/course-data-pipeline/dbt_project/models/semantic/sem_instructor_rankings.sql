{{ config(materialized='table') }}

WITH source AS (
    SELECT * FROM {{ ref('int_courses_standardized') }}
    WHERE instructor IS NOT NULL AND TRIM(instructor) != ''
),

instructor_stats AS (
    SELECT
        instructor,
        COUNT(*) AS course_count,
        COUNT(DISTINCT platform) AS platforms_count,
        STRING_AGG(DISTINCT platform, ', ') AS platforms,
        STRING_AGG(DISTINCT domain_name, ', ') AS domains,
        ROUND(AVG(rating), 2) AS avg_rating,
        SUM(enrolled_students) AS total_students,
        ROUND(AVG(enrolled_students), 0) AS avg_students_per_course,
        SUM(review_count) AS total_reviews,
        ROUND(AVG(engagement_rate_pct), 2) AS avg_engagement_pct,
        ROUND(AVG(value_score), 2) AS avg_value_score,
        ROUND(AVG(weighted_rating), 2) AS avg_weighted_rating,
        ROUND(
            (COALESCE(AVG(rating), 0) * 0.4)
            + (LN(COALESCE(SUM(enrolled_students), 0) + 1) * 0.3)
            + (COALESCE(AVG(engagement_rate_pct), 0) * 0.3),
            2
        ) AS composite_score
    FROM source
    GROUP BY instructor
    HAVING COUNT(*) >= 2
),

ranked AS (
    SELECT
        *,
        ROW_NUMBER() OVER (ORDER BY composite_score DESC) AS overall_rank,
        NTILE(10) OVER (ORDER BY composite_score DESC) AS decile
    FROM instructor_stats
)

SELECT * FROM ranked
