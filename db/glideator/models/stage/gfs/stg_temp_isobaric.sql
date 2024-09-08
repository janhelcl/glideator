WITH temperature AS (
	SELECT
		name AS launch,
		DATE(date) AS date,
		run,
		isobaric * 0.01 AS isobaric_lvl_hpa,
		"Temperature_isobaric" - 273.15 AS temperature_c
	FROM {{ source('gfs', 'temp_isobaric') }}
)
SELECT * FROM temperature