{{ config(materialized='view') }}

with source as (
    select * from {{ source('raw_data', 'udemy_final_data') }}
),

transformed as (
    select
        cast(course_id as varchar(100)) as course_id,
        trim([Course_Title]) as title,
        [Course_URL] as course_url,
        'Udemy' as platform,

        {{ standardize_language('[Language]') }} as language,

        trim([Description]) as description,
        replace(trim([Skills]), ' | ', ', ') as skills,
        [Level] as level,
        trim([Programming_Instructor]) as instructor,
        [Domain_Name] as domain_name,

        TRY_CONVERT(date, [Last_Update], 101) as last_updated,

        [Duration] as duration_raw,
        {{ parse_duration('[Duration]') }} as duration_hours,

        cast([No_of_Reviews] as int) as review_count,
        cast([rate] as float) as rating,
        cast([Price] as float) as price,
        [price_model] as price_model,
        cast([No_of_Students] as int) as enrolled_students,
        cast([offering_Type] as varchar(100)) as offering_type,

        row_number() over (
            partition by course_id
            order by TRY_CONVERT(date, [Last_Update], 101) desc
        ) as rn

    from source
    where TRY_CAST(course_id as int) is not null
)

select
    course_id,
    title,
    course_url,
    platform,
    language,
    description,
    skills,
    level,
    instructor,
    domain_name,
    offering_type,
    last_updated,
    duration_raw,
    duration_hours,
    review_count,
    rating,
    price,
    price_model,
    enrolled_students
from transformed
where rn = 1