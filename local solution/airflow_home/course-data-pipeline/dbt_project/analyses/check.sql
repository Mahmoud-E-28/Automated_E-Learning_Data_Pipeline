select count(*) from fact_offerings;

select count(*) from dim_offering;

select count(*) from dim_platform;

select count(*) from dim_domain;

select count(*) from dim_language;

select count(*) from dim_instructor;
---------------------------------
select
count(*) as total_rows,

sum(case when offering_sk is null then 1 else 0 end) as null_offering,

sum(case when platform_id is null then 1 else 0 end) as null_platform,

sum(case when domain_id is null then 1 else 0 end) as null_domain,

sum(case when language_id is null then 1 else 0 end) as null_language

from fact_offerings;


-------------------

select *
from dim_offering_type;
--------------
select
d.domain_name,
count(*) as courses
from fact_offerings f
join dim_domain d
on f.domain_id = d.domain_id
group by 1
order by 2 desc
limit 10;


-----------------

select count(*)
from snap_offerings;


-------
show tables;


---------
select count(*) from snap_offerings;


select
    count(*) as total,
    count(dof.offering_sk) as matched
from int_courses_standardized s
left join dim_offering dof
    on s.course_id = dof.offering_id;


select * from dim_offering limit 5;


select count(*) from dim_offering;

-----------
select count(*) from snap_offerings;


select
    count(*) as total,
    count(dof.offering_sk) as matched
from int_courses_standardized s
left join dim_offering dof
    on s.course_id = dof.offering_id;


select * from dim_offering limit 5;


select count(*) from dim_offering;


------
select
    is_current,
    count(*) as cnt
from dim_offering
group by is_current;


select
count(*) as total_rows,
sum(case when offering_sk is null then 1 else 0 end) as null_offering
from fact_offerings;

select *
from dim_offering
limit 5;


select *
from fact_offerings
limit 5;

select
sum(case when date_id is null then 1 else 0 end) as null_date,
sum(case when instructor_id is null then 1 else 0 end) as null_instructor,
sum(case when offering_type_id is null then 1 else 0 end) as null_offering_type
from fact_offerings;

select
    d.title,
    round(f.rating,2) as rating
from fact_offerings f
join dim_offering d
    on f.offering_sk = d.offering_sk
where f.rating is not null
order by rating desc
limit 10;

select
    dd.domain_name,
    count(*) as total_courses
from fact_offerings f
join dim_domain dd
    on f.domain_id = dd.domain_id
group by 1
order by 2 desc
limit 10;


select count(*) from fact_offerings;
select count(*)
from fact_offerings f
join dim_platform p
    on f.platform_id = p.platform_id
join dim_domain d
    on f.domain_id = d.domain_id
join dim_level l
    on f.level_id = l.level_id;