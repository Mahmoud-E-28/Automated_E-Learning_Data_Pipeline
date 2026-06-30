{{ config(materialized='view') }}

with source as (

    select *
    from {{ source('raw_data', 'coursera_final_data') }}

),

transformed as (

    select

        cast(course_id as varchar(100)) as course_id,

        ltrim(rtrim([Course_Title])) as title,

        [Course_URL] as course_url,

        'Coursera' as platform,

        {{ standardize_language('[Language]') }} as language,

        ltrim(rtrim([Description])) as description,

        ltrim(rtrim([Skill])) as skills,

        [Level] as level,

        ltrim(rtrim([Instructor])) as instructor,

        [Domain_Name] as domain_name,

        try_convert(date, [Last_Update], 101) as last_updated,

        [Duration] as duration_raw,

        {{ parse_duration('[Duration]') }} as duration_hours,

        cast([No__of_Reviews] as int) as review_count,

        cast([Rating] as float) as rating,

        cast([Price] as float) as price,

        [Price_Model] as price_model,

        cast([No__of_Students_enrolled] as int) as enrolled_students,

        cast([Type_of_Course] as varchar(100)) as offering_type,

        row_number() over (
            partition by course_id
            order by try_convert(date, [Last_Update], 101) desc
        ) as rn

    from source

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
  and course_id is not null