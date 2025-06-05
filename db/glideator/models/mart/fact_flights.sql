WITH sites AS (
	SELECT * FROM {{ ref('dim_sites')}}
),

flights AS (
	SELECT * FROM {{ ref('stg_flights')}}
),

filtered_flights AS (
	SELECT
		flights.*
	FROM flights
	INNER JOIN sites
	ON flights.site = sites.xc_name
	WHERE NOT (
		site_id = 185
		AND postgis.st_distancesphere(
			postgis.st_setsrid(postgis.st_makepoint(flights.longitude::double precision, flights.latitude::double precision), 4326),
			postgis.st_setsrid(postgis.st_makepoint(sites.longitude::double precision, sites.latitude::double precision), 4326)
		) > 10000  -- 10km in meters
	)
),

merged AS (
	SELECT
		date,
		start_time,
		pilot,
		CASE 
			WHEN site = 'Brosso' THEN 'Cavallaria' 
			WHEN site = 'Eged DK' THEN 'Eged'
			ELSE site 
		END AS site,
		type,
		length,
		points,
		glider_cat,
		glider,
		country,
		longitude,
		latitude
	FROM filtered_flights
)

SELECT * FROM merged