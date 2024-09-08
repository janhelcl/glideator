WITH pressure AS (
	SELECT
		name AS launch,
		DATE(date) AS date,
		run,
		"Pressure_surface" * 0.01 AS pressure_surface_hpa,
		"Pressure_reduced_to_MSL_msl" * 0.01 AS pressure_msl_hpa
	FROM {{ source('gfs', 'pressure') }}	
)
SELECT * FROM pressure