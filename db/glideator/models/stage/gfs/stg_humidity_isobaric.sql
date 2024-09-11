WITH humidity AS (
	SELECT
		name AS launch,
		DATE(date) AS date,
		run,
		isobaric * 0.01 AS isobaric_lvl_hpa,
		"Relative_humidity_isobaric" * 0.01 AS humidity_isobaric
	FROM {{ source('gfs', 'humidity_isobaric') }}
)
SELECT * FROM humidity