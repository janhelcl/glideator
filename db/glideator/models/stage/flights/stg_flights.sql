SELECT
	date,
	start_time,
	pilot,
	launch,
	type,
	length,
	points,
	glider_cat,
	glider
FROM {{ source('flights', 'flights') }}
WHERE launch != '?' AND glider_cat != 'HG'