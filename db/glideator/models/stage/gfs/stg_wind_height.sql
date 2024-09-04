WITH wind AS (
	SELECT
		*,
		180 + (180 / PI()) * ATAN2("u-component_of_wind_height_above_ground", "v-component_of_wind_height_above_ground") AS wind_direction_raw,
		SQRT(POWER("u-component_of_wind_height_above_ground", 2) + POWER("v-component_of_wind_height_above_ground", 2)) AS wind_speed
	FROM {{ source('gfs', 'wind_height') }}
),
transformed AS (
	SELECT
		name AS launch,
		DATE(date) AS date,
		run,
		height_above_ground4 AS height_m,
		"u-component_of_wind_height_above_ground" AS u_wind,
		"v-component_of_wind_height_above_ground" AS v_wind,
		wind_direction_raw - FLOOR(wind_direction_raw / 360) * 360 AS wind_direction_dgr, -- postgres doesn't have modulo for floats
		wind_speed AS wind_speed_ms
	FROM wind
)
SELECT * FROM transformed