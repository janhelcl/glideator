WITH wind AS (
	SELECT
		*,
		180 + (180 / PI()) * ATAN2("u-component_of_wind_isobaric", "v-component_of_wind_isobaric") AS wind_direction_raw,
		SQRT(POWER("u-component_of_wind_isobaric", 2) + POWER("v-component_of_wind_isobaric", 2)) AS wind_speed
	FROM {{ source('gfs', 'wind_isobaric') }}
),
transformed AS (
	SELECT
		name AS launch,
		DATE(date) AS date,
		run,
		isobaric * 0.01 AS isobaric_lvl_hpa,
		"u-component_of_wind_isobaric" AS u_wind_ms,
		"v-component_of_wind_isobaric" AS v_wind_ms,
		wind_direction_raw - FLOOR(wind_direction_raw / 360) * 360 AS wind_direction_dgr, -- postgres doesn't have modulo for floats
		wind_speed AS wind_speed_ms
	FROM wind
	WHERE run = 12
)
SELECT * FROM transformed