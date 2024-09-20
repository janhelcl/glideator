WITH temp_isobaric AS (
    SELECT
        launch,
        date,
        run,
        isobaric_lvl_hpa,
        temperature_c
    FROM {{ ref('stg_temp_isobaric')}}
),
temp_height AS (
    SELECT
        launch,
        date,
        run,
        height_lvl_m,
        temperature_c
    FROM {{ ref('stg_temp_height')}}
),
geopotential_isobaric AS (
    SELECT
        launch,
        date,
        run,
        isobaric_lvl_hpa,
        geopotential_height_m
    FROM {{ ref('stg_geopotential_isobaric')}}
),
geopotential_surface AS (
    SELECT
        launch,
        date,
        run,
        geopotential_height_m
    FROM {{ ref('stg_geopotential_surface')}}
),
temp_isobaric_amsl AS (
    SELECT
        t.launch,
        t.date,
        t.run,
        g.geopotential_height_m AS height_m,
        NULL::real AS height_lvl_m,
        t.isobaric_lvl_hpa,
        t.temperature_c,
        0 AS is_ground
    FROM temp_isobaric t
    JOIN geopotential_isobaric g
        ON t.launch = g.launch
        AND t.date = g.date
        AND t.isobaric_lvl_hpa = g.isobaric_lvl_hpa
),
temp_height_amsl AS (
    SELECT
        t.launch,
        t.date,
        t.run,
        t.height_lvl_m + g.geopotential_height_m AS height_m,
        t.height_lvl_m,
        NULL::real AS isobaric_lvl_hpa,
        t.temperature_c,
        CASE WHEN t.height_lvl_m = 2 THEN 1 ELSE 0 END AS is_ground
    FROM temp_height t
    JOIN geopotential_surface g
        ON t.launch = g.launch
        AND t.date = g.date
),
temp_amsl AS (
    SELECT
        *
    FROM temp_height_amsl
    UNION ALL
    SELECT
        *
    FROM temp_isobaric_amsl
),
is_above_ground AS (
    SELECT
        *,
        SUM(is_ground) OVER (PARTITION BY launch, date ORDER BY height_m) AS is_above_ground
    FROM temp_amsl
),
filtered AS (
    SELECT
        *
    FROM is_above_ground
    WHERE is_above_ground = 1
),
temp_amsl_w_ground_info AS (
    SELECT
        *,
        FIRST_VALUE(temperature_c) OVER (PARTITION BY launch, date ORDER BY height_m) AS temp_ground,
        FIRST_VALUE(height_m) OVER (PARTITION BY launch, date ORDER BY height_m) AS height_ground
    FROM filtered
),
temp_dalr AS (
    SELECT
        launch,
		date,
        run,
		height_m AS height_amsl,
		temperature_c,
        temp_ground - 9.8 * ((height_m - height_ground) / 1000) AS dalr
    FROM temp_amsl_w_ground_info
)

SELECT * FROM temp_dalr