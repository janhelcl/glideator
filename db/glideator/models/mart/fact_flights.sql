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
)

SELECT * FROM filtered_flights