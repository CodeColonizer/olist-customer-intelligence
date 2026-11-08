-- The raw file has ~1M rows with many points per zip code prefix.
-- Collapse to one approximate centroid per prefix. Points outside Brazil's
-- bounding box (a known issue in this dataset) are excluded.
drop view if exists stg_geolocation;
create view stg_geolocation as
select
    geolocation_zip_code_prefix          as zip_code_prefix,
    round(avg(geolocation_lat), 5)       as lat,
    round(avg(geolocation_lng), 5)       as lng,
    upper(max(geolocation_state))        as state,
    count(*)                             as points
from raw_geolocation
where geolocation_lat between -34 and 6
  and geolocation_lng between -74 and -34
group by geolocation_zip_code_prefix;
