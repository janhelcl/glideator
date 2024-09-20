WITH geopotential AS (
	SELECT
		name AS launch,
		DATE(date) AS date,
		run,
		isobaric * 0.01 AS isobaric_lvl_hpa,
		"Geopotential_height_isobaric" AS geopotential_height_m
	FROM {{ source('gfs', 'geopotential_isobaric') }}
	WHERE run = 12
)

SELECT * FROM geopotential