WITH temp AS (
	SELECT
		name AS launch,
		DATE(date) AS date,
		run,
		height_above_ground AS height_lvl_m,
		"Temperature_height_above_ground" - 273.15 AS temperature_c
	FROM {{ source('gfs', 'temp_height') }}
)
SELECT * FROM temp