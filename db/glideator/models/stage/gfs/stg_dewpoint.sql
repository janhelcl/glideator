WITH dewpoint AS (
	SELECT
		name AS launch,
		DATE(date) AS date,
		run,
		"Dewpoint_temperature_height_above_ground" - 273.15 AS dewpoint_c
	FROM {{ source('gfs', 'dewpoint') }}
	WHERE run = 12
)
SELECT * FROM dewpoint
