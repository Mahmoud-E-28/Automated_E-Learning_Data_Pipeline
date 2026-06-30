{{ config(materialized='view') }}

WITH combined AS (
    SELECT * FROM {{ ref('int_courses_combined') }}
),

enriched AS (
    SELECT
        course_id, platform, title, course_url, description, skills, instructor, language, domain_name,
        
        -- Level standardization
        CASE
            WHEN LOWER(TRIM(level)) IN ('beginner', 'beginner level', 'introductory') THEN 'Beginner'
            WHEN LOWER(TRIM(level)) IN ('intermediate', 'intermediate level') THEN 'Intermediate'
            WHEN LOWER(TRIM(level)) IN ('advanced', 'expert', 'advanced level') THEN 'Advanced'
            WHEN LOWER(TRIM(level)) IN ('all levels', 'all', 'mixed') THEN 'All Levels'
            ELSE 'Unknown'
        END AS level,

        -- إصلاح الـ Rating هنا: أي قيمة بره الـ 0-5 هنخليها NULL عشان التست ينجح، أو صلحها لـ 5
        CASE 
            WHEN rating < 0 OR rating > 5 THEN NULL 
            ELSE rating 
        END AS rating,
        
        review_count, enrolled_students, price,

        CASE
            WHEN LOWER(price_model) IN ('subscription', 'monthly_subscription') THEN 'Subscription'
            WHEN LOWER(price_model) = 'one time' THEN 'One Time'
            ELSE 'Unknown'
        END AS price_model,

        duration_hours, duration_raw,

        CASE
            WHEN price IS NULL THEN 'Unknown'
            WHEN price = 0 THEN 'Free'
            WHEN price < 500 THEN 'Cheap'
            WHEN price < 2000 THEN 'Medium'
            WHEN price < 5000 THEN 'Expensive'
            ELSE 'Premium'
        END AS price_category,

        CASE
            WHEN duration_hours IS NULL THEN 'Unknown'
            WHEN duration_hours < 5 THEN 'Short'
            WHEN duration_hours < 20 THEN 'Medium'
            WHEN duration_hours < 50 THEN 'Long'
            ELSE 'Extensive'
        END AS duration_category,

        ROUND(rating * LOG(ISNULL(enrolled_students, 0) + 1), 2) AS popularity_score,
        
        ROUND((CAST(review_count AS FLOAT) / NULLIF(enrolled_students, 0)) * 100, 2) AS engagement_rate_pct,

        ROUND(rating * LOG(ISNULL(review_count, 0) + 1), 2) AS weighted_rating,

        ROUND(price / NULLIF(duration_hours, 0), 2) AS cost_per_hour,

        COALESCE(offering_type, 'Unknown') AS offering_type,

        CASE
            WHEN LOWER(price_model) = 'one time' THEN price
            WHEN LOWER(price_model) IN ('subscription', 'monthly_subscription') 
                THEN ROUND(price * CEILING(duration_hours / 40.0), 2)
            ELSE price
        END AS estimated_total_cost,

        last_updated
    FROM combined
),

final AS (
    SELECT *,
        CASE 
            WHEN estimated_total_cost > 0 THEN ROUND((rating * LOG(ISNULL(enrolled_students, 0) + 1)) / estimated_total_cost, 2)
            ELSE NULL 
        END AS value_score
    FROM enriched
)

SELECT * FROM final