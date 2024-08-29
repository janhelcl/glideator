WITH mapping AS (
	SELECT * FROM {{ ref('seed_launch_mapping')}}
),

flights AS (
	SELECT * FROM {{ ref('stg_flights')}}
),

filtered_flights AS (
	SELECT
		flights.*
	FROM flights
	INNER JOIN mapping
	ON flights.launch = mapping.xcontest_name
)

SELECT * FROM filtered_flights