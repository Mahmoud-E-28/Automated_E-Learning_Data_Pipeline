{{ config(materialized='table') }}

SELECT
    ROW_NUMBER() OVER(
        ORDER BY course_id, dbt_valid_from
    ) AS offering_sk,

    course_id AS offering_id,
    title,
    description,
    skills,
    course_url,
    dbt_valid_from AS effective_from,
    dbt_valid_to AS effective_to,

    -- تعديل الـ CASE ليتوافق مع Fabric/T-SQL
    CASE
        WHEN dbt_valid_to IS NULL THEN 1
        ELSE 0
    END AS is_current

FROM {{ ref('offering_snapshot') }}