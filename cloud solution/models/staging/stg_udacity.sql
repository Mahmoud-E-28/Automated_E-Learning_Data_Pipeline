{{ config(materialized='view') }}

with source as (
    select * from {{ source('raw_data', 'udacity_final_data') }}
),

transformed as (
    select
        cast(course_id as varchar(100)) as course_id,
        trim(cast([Course_Title] as varchar(500))) as title,
        cast([Course_URL] as varchar(1000)) as course_url,
        'Udacity' as platform,

        {{ standardize_language('cast([Language] as varchar(100))') }} as language,

        trim(cast([Description] as varchar(max))) as description,
        trim(cast([Skill] as varchar(max))) as skills,
        cast([Level] as varchar(100)) as level,
        trim(cast([Programming_Instructor] as varchar(255))) as instructor,
        cast([Best_Category] as varchar(255)) as domain_name,

        TRY_CAST([Last_Update] as date) as last_updated,

        cast([Duration_Hours] as varchar(100)) as duration_raw,
        {{ parse_duration('cast([Duration_Hours] as varchar(100))') }} as duration_hours,

        cast([Review_Count] as int) as review_count,
        cast([Avg_Rating] as float) as rating,
        cast([monthly_price] as float) as price,
        cast([Price_Model] as varchar(100)) as price_model,
        cast([enrolled_students] as int) as enrolled_students,
        cast([offering_type] as varchar(100)) as offering_type,

        row_number() over (
            partition by course_id
            order by TRY_CAST([Last_Update] as datetime) desc
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