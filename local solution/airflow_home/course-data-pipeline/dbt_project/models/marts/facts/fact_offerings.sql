{{ config(materialized='table') }}

WITH source_data AS (

    SELECT *
    FROM {{ ref('int_courses_standardized') }}

),

final AS (

    SELECT

        dof.offering_sk,
        dp.platform_id,
        dd.domain_id,
        dl.level_id,
        dlang.language_id,

        COALESCE(di.instructor_id,-1) AS instructor_id,
        COALESCE(dot.offering_type_id,-1) AS offering_type_id,
        COALESCE(dt.date_id,-1) AS date_id,

        s.price,
        s.rating,
        s.review_count,
        s.enrolled_students,
        s.duration_hours,

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
        ON COALESCE(s.instructor,'Unknown Instructor')
        = di.instructor_name

    LEFT JOIN {{ ref('dim_offering_type') }} dot
        ON COALESCE(s.offering_type,'Unknown')
        = dot.offering_type

    LEFT JOIN {{ ref('dim_date') }} dt
        ON CAST(strftime(s.last_updated,'%Y%m%d') AS INTEGER) = dt.date_id

    LEFT JOIN {{ ref('dim_offering') }} dof
        ON s.course_id = dof.offering_id
        AND dof.is_current = TRUE

)

SELECT *
FROM final