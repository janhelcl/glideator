WITH

dewpoint AS (
	SELECT
		launch,
		date,
		run,
		dewpoint_c
	FROM {{ ref('stg_dewpoint')}}
),
geopotential_isobaric AS (
	SELECT
		launch,
		date,
		run,
		ARRAY_AGG(geopotential_height_m ORDER BY isobaric_lvl_hpa DESC) AS geopotential_isobaric_height_m,
		ARRAY_AGG(isobaric_lvl_hpa ORDER BY isobaric_lvl_hpa DESC) AS isobaric_lvl_hpa
	FROM {{ ref('stg_geopotential_isobaric')}}
	GROUP BY launch, date, run
),
geopotential_surface AS (
	SELECT
		launch,
		date,
		run,
		geopotential_height_m AS geopotential_surface_height_m
	FROM {{ ref('stg_geopotential_surface')}}
),
gust AS (
	SELECT
		launch,
		date,
		run,
		gust_speed_ms
	FROM {{ ref('stg_gust')}}
),
humidity_isobaric AS (
	SELECT
		launch,
		date,
		run,
		ARRAY_AGG(humidity_isobaric ORDER BY isobaric_lvl_hpa DESC) AS humidity_isobaric
	FROM {{ ref('stg_humidity_isobaric')}}
	GROUP BY launch, date, run
),
precipitation AS (
	SELECT
		launch,
		date,
		run,
		precipitable_water_kgm2,
		precipitation_rate_mmhr
	FROM {{ ref('stg_precipitation')}}
),
pressure AS (
	SELECT
		launch,
		date,
		run,
		pressure_surface_hpa,
		pressure_msl_hpa
	FROM {{ ref('stg_pressure')}}
),
temp_height AS (
	SELECT
		launch,
		date,
		run,
		ARRAY_AGG(height_lvl_m ORDER BY height_lvl_m) AS height_temp_lvl_m,
		ARRAY_AGG(temperature_c ORDER BY height_lvl_m) AS temperature_c_agl
	FROM {{ ref('stg_temp_height')}}
	GROUP BY launch, date, run
),
temp_isobaric AS (
	SELECT
		launch,
		date,
		run,
		ARRAY_AGG(temperature_c ORDER BY isobaric_lvl_hpa DESC) AS temperature_c_isobaric
	FROM {{ ref('stg_temp_isobaric')}}
	GROUP BY launch, date, run
),
wind_height AS (
	SELECT	
		launch,
		date,
		run,
		ARRAY_AGG(height_m ORDER BY height_m) AS height_wind_lvl_m,
		ARRAY_AGG(u_wind_ms ORDER BY height_m) AS u_wind_ms_agl,
		ARRAY_AGG(v_wind_ms ORDER BY height_m) AS v_wind_ms_agl
	FROM {{ ref('stg_wind_height')}}
	GROUP BY launch, date, run
),
wind_isobaric AS (
	SELECT	
		launch,
		date,
		run,
		ARRAY_AGG(u_wind_ms ORDER BY isobaric_lvl_hpa DESC) AS u_wind_ms_isobaric,
		ARRAY_AGG(v_wind_ms ORDER BY isobaric_lvl_hpa DESC) AS v_wind_ms_isobaric
	FROM {{ ref('stg_wind_isobaric')}}
	GROUP BY launch, date, run
),
temp_amsl AS (
    SELECT
        launch,
        date,
		run,
        ARRAY_AGG(dalr ORDER BY height_amsl) AS dalr,
        ARRAY_AGG(temperature_c ORDER BY height_amsl) AS temperature_c_amsl,
        ARRAY_AGG(height_amsl ORDER BY height_amsl) AS height_amsl
    FROM {{ ref('int_temp_amsl')}}
    GROUP BY launch, date, run
),
joined AS (
	SELECT
		dewpoint.launch,
		dewpoint.date,
		dewpoint.run,

		geopotential_isobaric.isobaric_lvl_hpa,
		temp_height.height_temp_lvl_m,
		wind_height.height_wind_lvl_m,
		temp_amsl.height_amsl,

		dewpoint.dewpoint_c,
		geopotential_isobaric.geopotential_isobaric_height_m,
		geopotential_surface.geopotential_surface_height_m,
		gust.gust_speed_ms,
		humidity_isobaric.humidity_isobaric,
		precipitation.precipitable_water_kgm2,
		precipitation.precipitation_rate_mmhr,
		pressure.pressure_surface_hpa,
		pressure.pressure_msl_hpa,
		temp_height.temperature_c_agl,
		temp_isobaric.temperature_c_isobaric,
		wind_height.u_wind_ms_agl,
		wind_height.v_wind_ms_agl,
		wind_isobaric.u_wind_ms_isobaric,
		wind_isobaric.v_wind_ms_isobaric,
		temp_amsl.dalr,
		temp_amsl.temperature_c_amsl
		
	FROM dewpoint
	JOIN geopotential_isobaric 
		ON dewpoint.launch = geopotential_isobaric.launch 
		AND dewpoint.date = geopotential_isobaric.date 
		AND dewpoint.run = geopotential_isobaric.run
	JOIN geopotential_surface
		ON dewpoint.launch = geopotential_surface.launch 
		AND dewpoint.date = geopotential_surface.date 
		AND dewpoint.run = geopotential_surface.run
	JOIN gust
		ON dewpoint.launch = gust.launch 
		AND dewpoint.date = gust.date 
		AND dewpoint.run = gust.run
	JOIN humidity_isobaric
		ON dewpoint.launch = humidity_isobaric.launch 
		AND dewpoint.date = humidity_isobaric.date 
		AND dewpoint.run = humidity_isobaric.run
	JOIN precipitation
		ON dewpoint.launch = precipitation.launch 
		AND dewpoint.date = precipitation.date 
		AND dewpoint.run = precipitation.run
	JOIN pressure
		ON dewpoint.launch = pressure.launch 
		AND dewpoint.date = pressure.date 
		AND dewpoint.run = pressure.run
	JOIN temp_height
		ON dewpoint.launch = temp_height.launch 
		AND dewpoint.date = temp_height.date 
		AND dewpoint.run = temp_height.run
	JOIN temp_isobaric
		ON dewpoint.launch = temp_isobaric.launch 
		AND dewpoint.date = temp_isobaric.date 
		AND dewpoint.run = temp_isobaric.run
	JOIN wind_height
		ON dewpoint.launch = wind_height.launch 
		AND dewpoint.date = wind_height.date
		AND dewpoint.run = wind_height.run
	JOIN wind_isobaric
		ON dewpoint.launch = wind_isobaric.launch 
		AND dewpoint.date = wind_isobaric.date 
		AND dewpoint.run = wind_isobaric.run
	JOIN temp_amsl
		ON dewpoint.launch = temp_amsl.launch 
		AND dewpoint.date = temp_amsl.date 
		AND dewpoint.run = temp_amsl.run
)

SELECT * FROM joined