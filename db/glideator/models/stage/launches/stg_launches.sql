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
	END is_official,
	active AS is_active,
	loaded_dttm AS loaded_at
FROM source.launches