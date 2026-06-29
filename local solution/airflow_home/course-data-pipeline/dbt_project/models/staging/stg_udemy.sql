{{ config(materialized='view') }}

with source as (
    select * from {{ source('raw_data', 'udemy_final_data') }}
),

transformed as (
    select
        cast(course_id as varchar) as course_id,
        trim("Course_Title") as title,
        "Course_URL" as course_url,
        'Udemy' as platform,
        
        -- Language standardization using macro
        {{ standardize_language('"Language"') }} as language,
        
        trim("Description") as description,
        replace(trim("Skills"), ' | ', ', ') as skills,
        "Level" as level,
        trim("Programming_Instructor") as instructor,
        "Domain_Name" as domain_name,
        strptime("Last_Update", '%m/%d/%Y')::date as last_updated,
        
        -- Duration: keep raw + parsed
        "Duration" as duration_raw,
        {{ parse_duration('"Duration"') }} as duration_hours,
        
        cast("No_of_Reviews" as integer) as review_count,
        cast("rate" as float) as rating,
        cast("Price" as float) as price,
        "price model" as price_model,
        cast("No_of_Students" as integer) as enrolled_students,
        cast("offering_Type" as varchar) as offering_type,
        row_number() over (
            partition by course_id 
            order by strptime("Last_Update", '%m/%d/%Y') desc nulls last
        ) as rn
    from source
    where try_cast(course_id as integer) is not null
)

select 
    course_id, title, course_url, platform, language, description, skills,
    level, instructor, domain_name,offering_type, last_updated, 
    duration_raw, duration_hours,
    review_count, rating, price, price_model, enrolled_students
from transformed 
where rn = 1