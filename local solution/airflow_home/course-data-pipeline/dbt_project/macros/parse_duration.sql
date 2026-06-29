{% macro parse_duration(column_name) %}
    case
        when {{ column_name }} is null then null
        when trim(cast({{ column_name }} as varchar)) = '' then null
        
        -- Minutes → hours (e.g., "20 minutes" → 0.33)
        when lower(trim(cast({{ column_name }} as varchar))) like '%minute%' 
            or lower(trim(cast({{ column_name }} as varchar))) like '%min%'
            then round(
                try_cast(regexp_extract(trim(cast({{ column_name }} as varchar)), '[\d.]+') as float) / 60.0,
                2
            )
        
        -- Hours
        when lower(trim(cast({{ column_name }} as varchar))) like '%hour%' 
            or lower(trim(cast({{ column_name }} as varchar))) like '%hr%'
            then try_cast(regexp_extract(trim(cast({{ column_name }} as varchar)), '[\d.]+') as float)
        
        -- Plain numeric (assumed hours)
        when regexp_matches(trim(cast({{ column_name }} as varchar)), '^[\d.]+$')
            then try_cast(trim(cast({{ column_name }} as varchar)) as float)
        
        else null
    end
{% endmacro %}