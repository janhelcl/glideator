SELECT
	name,
	latitude,
	longitude,
	altitude,
	superelevation,
	wind_usable_from,
	wind_usable_to,
	wind_optimal_from,
	wind_optimal_to,
	CASE
		WHEN flying_status = 1 THEN true
		WHEN flying_status = 2 THEN true
		ELSE false
	END official,
	active,
	loaded_dttm
FROM source.launches