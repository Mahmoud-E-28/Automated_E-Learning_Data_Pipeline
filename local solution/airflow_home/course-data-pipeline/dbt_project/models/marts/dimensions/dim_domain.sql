{{ config(materialized='table') }}

select

    row_number() over(order by domain_name) as domain_id,

    domain_name

from (

    select distinct domain_name

    from {{ ref('int_courses_standardized') }}

)