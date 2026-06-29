{% snapshot offering_snapshot %}

{{
    config(
        target_schema='snapshots',
        unique_key='course_id',
        strategy='check',
        check_cols=['title', 'description', 'skills', 'course_url']
    )
}}

SELECT * 
FROM {{ ref('int_courses_standardized') }}

{% endsnapshot %}