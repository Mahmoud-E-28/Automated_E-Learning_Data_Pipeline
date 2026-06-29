{{ config(materialized='view') }}

with coursera as (select * from {{ ref('stg_coursera') }}),

udacity as (select * from {{ ref('stg_udacity') }}),

udemy as (select * from {{ ref('stg_udemy') }}),

combined as (
    select * from coursera
    union all by name
    select * from udacity
    union all by name
    select * from udemy)

select * from combined