{{ config(materialized='table') }}

WITH source_data AS (

    SELECT *
    FROM {{ ref('int_courses_standardized') }}

),

final AS (

    SELECT

        -- Foreign Keys
        COALESCE(dof.offering_sk, -1)      AS offering_sk,
        COALESCE(dp.platform_id, -1)       AS platform_id,
        COALESCE(dd.domain_id, -1)         AS domain_id,
        COALESCE(dl.level_id, -1)          AS level_id,
        COALESCE(dlang.language_id, -1)    AS language_id,
        COALESCE(di.instructor_id, -1)     AS instructor_id,
        COALESCE(dot.offering_type_id, -1) AS offering_type_id,
        COALESCE(dt.date_id, -1)           AS date_id,

        -- Base Metrics
        s.price,
        s.rating,
        s.review_count,
        s.enrolled_students,
        s.duration_hours,

        -- Categories
        s.price_category,
        s.duration_category,

        -- Calculated Metrics
        s.popularity_score,
        s.engagement_rate_pct,
        s.weighted_rating,
        s.cost_per_hour,
        s.estimated_total_cost,
        s.value_score

    FROM source_data s

    LEFT JOIN {{ ref('dim_platform') }} dp
        ON s.platform = dp.platform_name

    LEFT JOIN {{ ref('dim_domain') }} dd
        ON s.domain_name = dd.domain_name

    LEFT JOIN {{ ref('dim_level') }} dl
        ON s.level = dl.level_name

    LEFT JOIN {{ ref('dim_language') }} dlang
        ON s.language = dlang.language_name

    LEFT JOIN {{ ref('dim_instructor') }} di
        ON COALESCE(s.instructor, 'Unknown Instructor')
        = di.instructor_name

    LEFT JOIN {{ ref('dim_offering_type') }} dot
        ON COALESCE(s.offering_type, 'Unknown')
        = dot.offering_type

    LEFT JOIN {{ ref('dim_date') }} dt
        ON CAST(CONVERT(VARCHAR(8), s.last_updated, 112) AS INT)
        = dt.date_id

    LEFT JOIN {{ ref('dim_offering') }} dof
        ON s.course_id = dof.offering_id
        AND dof.is_current = 1

)

SELECT *
FROM final