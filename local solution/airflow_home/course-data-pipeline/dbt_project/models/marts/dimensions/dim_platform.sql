{{ config(materialized='table') }}

select
    row_number() over(order by platform) as platform_id,
    platform as platform_name

from (
    select distinct platform
    from {{ ref('int_courses_standardized') }})