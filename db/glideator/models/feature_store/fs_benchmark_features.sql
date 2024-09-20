WITH
aggregated AS (
    SELECT
        launch,
        date,
        ARRAY_AGG(dalr ORDER BY height_amsl) AS dalr,
        ARRAY_AGG(temperature_c ORDER BY height_amsl) AS temperature_c,
        ARRAY_AGG(height_amsl ORDER BY height_amsl) AS height_amsl
    FROM {{ ref('int_temp_amsl')}}
    GROUP BY 1, 2
),
dewpoint AS (
    SELECT
        launch,
        date,
        dewpoint_c
    FROM {{ ref('stg_dewpoint')}}
),
wind AS (
    SELECT
        launch,
        date,
        u_wind_ms,
        v_wind_ms,
        wind_direction_dgr,
        wind_speed_ms
    FROM {{ ref('stg_wind_height')}}
    WHERE height_m = 10
),
water AS (
    SELECT
        launch,
        date,
        precipitable_water_kgm2
    FROM {{ ref('stg_precipitation')}}
),
gust AS (
    SELECT
        launch,
        date,
        gust_speed_ms
    FROM {{ ref('stg_gust')}}
),
pressure AS (
    SELECT
        launch,
        date,
        pressure_surface_hpa
    FROM {{ ref('stg_pressure')}}
),
launches AS (
    SELECT 
    	name AS launch,
    	altitude,
    	superelevation,
        usable_wind_range1[1] AS usable_range1_from,
        usable_wind_range1[2] AS usable_range1_to,
        usable_wind_range2[1] AS usable_range2_from,
        usable_wind_range2[2] AS usable_range2_to
    FROM {{ ref('dim_launches')}}
),
features AS (
    SELECT
        aggregated.launch,
        aggregated.date,

        wind.u_wind_ms,
        wind.v_wind_ms,
        wind.wind_direction_dgr,
        wind.wind_speed_ms,
        gust.gust_speed_ms,
        dewpoint.dewpoint_c AS dewpoint_c_surface,
        aggregated.temperature_c[1] AS temperature_c_surface,
        pressure.pressure_surface_hpa,
        water.precipitable_water_kgm2,

        launches.altitude,
        launches.superelevation,
        launches.usable_range1_from,
        launches.usable_range1_to,
        launches.usable_range2_from,
        launches.usable_range2_to,

        aggregated.temperature_c,
        aggregated.height_amsl,
        aggregated.dalr

    FROM aggregated
    JOIN dewpoint
        ON aggregated.launch = dewpoint.launch
        AND aggregated.date = dewpoint.date
    JOIN wind
        ON aggregated.launch = wind.launch
        AND aggregated.date = wind.date
    JOIN launches
        ON aggregated.launch = launches.launch
    JOIN water
        ON aggregated.launch = water.launch
        AND aggregated.date = water.date
    JOIN gust
        ON aggregated.launch = gust.launch
        AND aggregated.date = gust.date
    JOIN pressure
        ON aggregated.launch = pressure.launch
        AND aggregated.date = pressure.date
)

SELECT * FROM features