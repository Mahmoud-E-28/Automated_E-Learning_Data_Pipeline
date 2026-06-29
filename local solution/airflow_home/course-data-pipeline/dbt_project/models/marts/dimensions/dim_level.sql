{{ config(materialized='table') }}

select

    row_number() over(order by level) as level_id,

    level as level_name

from (

    select distinct level

    from {{ ref('int_courses_standardized') }}

)