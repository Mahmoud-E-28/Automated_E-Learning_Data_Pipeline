{{ config(materialized='table') }}

with dates as (

    select distinct

        cast(strftime(last_updated,'%Y%m%d') as integer) as date_id,

        last_updated as full_date,

        extract(day from last_updated) as day,

        extract(month from last_updated) as month,

        extract(quarter from last_updated) as quarter,

        extract(year from last_updated) as year

    from {{ ref('int_courses_standardized') }}

    where last_updated is not null

),

unknown_date as (

    select
        -1 as date_id,
        null as full_date,
        null as day,
        null as month,
        null as quarter,
        null as year

)

select * from dates

union all

select * from unknown_date