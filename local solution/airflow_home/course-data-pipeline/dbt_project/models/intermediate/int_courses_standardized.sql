{{ config(materialized='view') }}

WITH combined AS (

    SELECT *
    FROM {{ ref('int_courses_combined') }}

),

enriched AS (

    SELECT

        -- Identifiers & descriptive fields
        course_id,
        platform,
        title,
        course_url,
        description,
        skills,
        instructor,
        language,
        domain_name,

        -- Level standardization
        CASE
            WHEN LOWER(TRIM(level)) IN ('beginner', 'beginner level', 'introductory') THEN 'Beginner'
            WHEN LOWER(TRIM(level)) IN ('intermediate', 'intermediate level') THEN 'Intermediate'
            WHEN LOWER(TRIM(level)) IN ('advanced', 'expert', 'advanced level') THEN 'Advanced'
            WHEN LOWER(TRIM(level)) IN ('all levels', 'all', 'mixed') THEN 'All Levels'
            ELSE 'Unknown'
        END AS level,

        -- Numeric fields
        rating,
        review_count,
        enrolled_students,
        price,

        -- Price model standardization
        CASE
            WHEN LOWER(price_model) IN ('subscription','monthly_subscription')
                THEN 'Subscription'
            WHEN LOWER(price_model) = 'one time'
                THEN 'One Time'
            ELSE 'Unknown'
        END AS price_model,

        duration_hours,
        duration_raw,

        -- Price category
        CASE
            WHEN price IS NULL THEN 'Unknown'
            WHEN price = 0 THEN 'Free'
            WHEN price < 500 THEN 'Cheap'
            WHEN price < 2000 THEN 'Medium'
            WHEN price < 5000 THEN 'Expensive'
            ELSE 'Premium'
        END AS price_category,

        -- Duration category
        CASE
            WHEN duration_hours IS NULL THEN 'Unknown'
            WHEN duration_hours < 5 THEN 'Short'
            WHEN duration_hours < 20 THEN 'Medium'
            WHEN duration_hours < 50 THEN 'Long'
            ELSE 'Extensive'
        END AS duration_category,

        -- Popularity score
        CASE
            WHEN rating IS NULL OR enrolled_students IS NULL THEN NULL
            ELSE ROUND(rating * LN(enrolled_students + 1), 2)
        END AS popularity_score,

        -- Engagement rate
        CASE
            WHEN enrolled_students IS NULL OR enrolled_students = 0 THEN NULL
            WHEN review_count IS NULL THEN 0
            ELSE ROUND(
                (CAST(review_count AS FLOAT) / enrolled_students) * 100,
                2
            )
        END AS engagement_rate_pct,

        -- Weighted rating
        CASE
            WHEN rating IS NULL THEN NULL
            ELSE ROUND(
                rating * LN(COALESCE(review_count,0) + 1),
                2
            )
        END AS weighted_rating,

        -- Cost per learning hour
        CASE
            WHEN price IS NULL
                 OR duration_hours IS NULL
                 OR duration_hours = 0
            THEN NULL
            ELSE ROUND(price / duration_hours, 2)
        END AS cost_per_hour,

        -- Offering type
        COALESCE(offering_type,'Unknown') AS offering_type,

        -- Estimated total cost
        CASE
            WHEN price IS NULL
                 OR duration_hours IS NULL
            THEN NULL

            WHEN LOWER(price_model) = 'one time'
            THEN price

            WHEN LOWER(price_model) IN
                ('subscription','monthly_subscription')
            THEN ROUND(
                price * CEIL(duration_hours / 40.0),
                2
            )

            ELSE price
        END AS estimated_total_cost,

        last_updated

    FROM combined

),

final AS (

    SELECT

        *,

        -- Value score
        CASE
            WHEN estimated_total_cost IS NULL
                 OR estimated_total_cost = 0
                 OR rating IS NULL
                 OR enrolled_students IS NULL
            THEN NULL

            ELSE ROUND(
                (rating * LN(enrolled_students + 1))
                / estimated_total_cost,
                2
            )

        END AS value_score

    FROM enriched

)

SELECT *
FROM final