WITH sites AS (
    SELECT
        *,
        glideator.get_gfs_coords(latitude::numeric, longitude::numeric) AS gfs_coords
    FROM {{ ref('seed_sites') }}
)

SELECT
    site_id,
    name,
    xc_name,
    longitude,
    latitude,
    altitude,
    gfs_coords[1] AS lat_gfs,
    gfs_coords[2] AS lon_gfs,
    source
FROM sites