{{ config(materialized='view') }}

with source as (
    select * from {{ source('raw_data', 'udacity_final_data') }}
),

transformed as (
    select
        cast(course_id as varchar) as course_id,
        trim(cast("Course_Title" as varchar)) as title,
        cast("Course_URL" as varchar) as course_url,
        'Udacity' as platform,
        
        -- Language standardization using macro
        {{ standardize_language('cast("Language" as varchar)') }} as language,
        
        trim(cast("Description" as varchar)) as description,
        trim(cast("Skill" as varchar)) as skills,
        cast("Level" as varchar) as level,
        trim(cast("Programming Instructor" as varchar)) as instructor,
        cast("Best_Category" as varchar) as domain_name,
        try_cast("Last Update" as date) as last_updated,
        
        -- Duration: keep raw + parsed
        cast("Duration_Hours" as varchar) as duration_raw,
        {{ parse_duration('cast("Duration_Hours" as varchar)') }} as duration_hours,
        
        cast("Review_Count" as integer) as review_count,
        cast("Avg_Rating" as float) as rating,
        cast("monthly_price" as float) as price,
        cast("Price_Model" as varchar) as price_model,
        cast("enrolled_students" as integer) as enrolled_students,
        cast("offering_type" as varchar) as offering_type,
        row_number() over (
            partition by course_id 
            order by try_cast("Last Update" as timestamp) desc nulls last
        ) as rn
    from source
)

select 
    course_id, title, course_url, platform, language, description, skills,
    level, instructor, domain_name,offering_type, last_updated, 
    duration_raw, duration_hours,
    review_count, rating, price, price_model, enrolled_students
from transformed 
where rn = 1