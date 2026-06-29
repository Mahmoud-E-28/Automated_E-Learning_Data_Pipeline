{{ config(materialized='table') }}

with offering_types as (

    select distinct
        coalesce(offering_type,'Unknown') as offering_type
    from {{ ref('int_courses_standardized') }})

select

    case
        when offering_type = 'Unknown' then -1
        else row_number() over(order by offering_type)
    end as offering_type_id,

    offering_type

from offering_types