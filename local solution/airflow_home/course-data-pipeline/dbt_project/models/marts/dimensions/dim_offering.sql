{{ config(materialized='table') }}

select

    row_number() over(
        order by course_id, dbt_valid_from
    ) as offering_sk,

    course_id as offering_id,

    title,

    description,

    skills,

    course_url,

    dbt_valid_from as effective_from,

    dbt_valid_to as effective_to,

    case
        when dbt_valid_to is null
        then true
        else false
    end as is_current

from {{ ref('offering_snapshot') }}