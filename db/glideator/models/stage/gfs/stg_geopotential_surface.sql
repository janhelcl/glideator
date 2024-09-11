WITH geopotential AS (
	SELECT
		name AS launch,
		DATE(date) AS date,
		run,
		"Geopotential_height_surface" AS geopotential_height_m
	FROM {{ source('gfs', 'geopotential_height_surface') }}
)

SELECT * FROM geopotential

