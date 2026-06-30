{% macro parse_duration(column_name) %}

case

    when {{ column_name }} is null then null

    when ltrim(rtrim(cast({{ column_name }} as varchar(100)))) = ''
        then null

    -- Minutes
    when lower(cast({{ column_name }} as varchar(100))) like '%minute%'
      or lower(cast({{ column_name }} as varchar(100))) like '%min%'
    then round(
            try_cast(
                left(
                    cast({{ column_name }} as varchar(100)),
                    patindex('%[^0-9.]%', cast({{ column_name }} as varchar(100)) + 'x') - 1
                )
            as float) / 60.0
        ,2)

    -- Hours
    when lower(cast({{ column_name }} as varchar(100))) like '%hour%'
      or lower(cast({{ column_name }} as varchar(100))) like '%hr%'
    then
        try_cast(
            left(
                cast({{ column_name }} as varchar(100)),
                patindex('%[^0-9.]%', cast({{ column_name }} as varchar(100)) + 'x') - 1
            )
        as float)

    -- Pure numeric
    when try_cast(cast({{ column_name }} as varchar(100)) as float) is not null
    then try_cast(cast({{ column_name }} as varchar(100)) as float)

    else null

end

{% endmacro %}