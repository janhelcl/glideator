WITH gust AS (
	SELECT
		name AS launch,
		DATE(date) AS date,
		run,
		"Wind_speed_gust_surface" AS gust_speed_ms
	FROM {{ source('gfs', 'gust') }}
)

SELECT * FROM gust