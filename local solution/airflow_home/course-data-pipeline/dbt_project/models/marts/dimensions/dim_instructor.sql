{{ config(materialized='table') }}

with instructors as (
    select distinct
        coalesce(instructor,'Unknown Instructor') as instructor_name
    from {{ ref('int_courses_standardized') }})

select
    case
        when instructor_name = 'Unknown Instructor' then -1
        else row_number() over(order by instructor_name)
    end as instructor_id,
    instructor_name

from instructors