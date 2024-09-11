WITH precipitation AS (
	SELECT
		name AS launch,
		DATE(date) AS date,
		run,
		"Precipitable_water_entire_atmosphere_single_layer" AS precipitable_water_kgm2,
		"Precipitation_rate_surface" * 3600 AS precipitation_rate_mmhr
	FROM {{ source('gfs', 'precipitation') }}
)

SELECT * FROM precipitation