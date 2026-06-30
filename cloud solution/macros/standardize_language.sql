{% macro standardize_language(column_name) %}
    case
        when {{ column_name }} is null then null
        
        -- English
        when lower({{ column_name }}) in ('english', 'en', 'en-us', 'en-gb', 'en-in', 'en-au', 'en-ca') 
            then 'English'
        
        -- Spanish
        when lower({{ column_name }}) in ('spanish', 'es', 'es-es', 'es-la', 'es-mx', 'es-cl', 'es-co', 'es-ve', 'es-ar') 
            then 'Spanish'
        
        -- Portuguese
        when lower({{ column_name }}) in ('portuguese', 'pt', 'pt-br', 'pt-pt') 
            then 'Portuguese'
        
        -- French
        when lower({{ column_name }}) in ('french', 'fr', 'fr-fr', 'fr-ca') 
            then 'French'
        
        -- German
        when lower({{ column_name }}) in ('german', 'de', 'de-de') 
            then 'German'
        
        -- Arabic
        when lower({{ column_name }}) in ('arabic', 'ar', 'ar-sa', 'ar-eg') 
            then 'Arabic'
        
        -- Chinese
        when lower({{ column_name }}) in ('chinese', 'zh', 'zh-cn', 'zh-tw', 'zh-hk') 
            then 'Chinese'
        
        -- Japanese
        when lower({{ column_name }}) in ('japanese', 'ja', 'ja-jp') 
            then 'Japanese'
        
        -- Korean
        when lower({{ column_name }}) in ('korean', 'ko', 'ko-kr') 
            then 'Korean'
        
        -- Russian
        when lower({{ column_name }}) in ('russian', 'ru', 'ru-ru') 
            then 'Russian'
        
        -- Italian
        when lower({{ column_name }}) in ('italian', 'it', 'it-it') 
            then 'Italian'
        
        -- Turkish
        when lower({{ column_name }}) in ('turkish', 'tr', 'tr-tr') 
            then 'Turkish'
        
        -- Dutch
        when lower({{ column_name }}) in ('dutch', 'nl', 'nl-nl', 'nl-be') 
            then 'Dutch'
        
        -- Hindi
        when lower({{ column_name }}) in ('hindi', 'hi', 'hi-in') 
            then 'Hindi'
        
        -- Polish
        when lower({{ column_name }}) in ('polish', 'pl', 'pl-pl') 
            then 'Polish'
        
        -- Swedish
        when lower({{ column_name }}) in ('swedish', 'sv', 'sv-se') 
            then 'Swedish'
        
        -- Indonesian
        when lower({{ column_name }}) in ('indonesian', 'id', 'id-id') 
            then 'Indonesian'
        
        -- Vietnamese
        when lower({{ column_name }}) in ('vietnamese', 'vi', 'vi-vn') 
            then 'Vietnamese'
        
        -- Thai
        when lower({{ column_name }}) in ('thai', 'th', 'th-th') 
            then 'Thai'
        
        -- Hebrew
        when lower({{ column_name }}) in ('hebrew', 'he', 'he-il') 
            then 'Hebrew'
        
        -- Greek
        when lower({{ column_name }}) in ('greek', 'el', 'el-gr') 
            then 'Greek'
        
        -- Czech
        when lower({{ column_name }}) in ('czech', 'cs', 'cs-cz') 
            then 'Czech'
        
        -- Ukrainian
        when lower({{ column_name }}) in ('ukrainian', 'uk', 'uk-ua') 
            then 'Ukrainian'
        
        -- Persian
        when lower({{ column_name }}) in ('persian', 'farsi', 'fa', 'fa-ir') 
            then 'Persian'
        
        -- Urdu
        when lower({{ column_name }}) in ('urdu', 'ur', 'ur-pk') 
            then 'Urdu'
        
        -- Bengali
        when lower({{ column_name }}) in ('bengali', 'bn', 'bn-in') 
            then 'Bengali'
        
        -- Romanian
        when lower({{ column_name }}) in ('romanian', 'ro', 'ro-ro') 
            then 'Romanian'
        
        -- Hungarian
        when lower({{ column_name }}) in ('hungarian', 'hu', 'hu-hu') 
            then 'Hungarian'
        
        -- Danish
        when lower({{ column_name }}) in ('danish', 'da', 'da-dk') 
            then 'Danish'
        
        -- Finnish
        when lower({{ column_name }}) in ('finnish', 'fi', 'fi-fi') 
            then 'Finnish'
        
        -- Norwegian
        when lower({{ column_name }}) in ('norwegian', 'no', 'nb-no', 'nn-no') 
            then 'Norwegian'
        
        else 'Other / Unknown'
    end
{% endmacro %}