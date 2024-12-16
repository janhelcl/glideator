SELECT
	date,
	start_time,
	pilot,
	launch AS site,
	type,
	length,
	points,
	glider_cat,
	glider,
	country,
	latitude AS longitude,
	longitude AS latitude
FROM {{ source('flights', 'flights') }}
WHERE launch != '?' AND glider_cat != 'HG'