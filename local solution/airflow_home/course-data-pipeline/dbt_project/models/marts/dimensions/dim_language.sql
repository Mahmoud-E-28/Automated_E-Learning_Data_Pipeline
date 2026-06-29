{{ config(materialized='table') }}

select

    row_number() over(order by language) as language_id,

    language as language_name

from (

    select distinct language

    from {{ ref('int_courses_standardized') }}

)