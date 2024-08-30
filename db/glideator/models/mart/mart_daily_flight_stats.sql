WITH flights AS (
	SELECT * FROM {{ ref('fact_flights')}}
),

launches AS (
	SELECT * FROM {{ ref('dim_launches')}}
),

date_range AS (
	SELECT
		DATE_TRUNC('month', MIN(date)) AS min_date,
		DATE_TRUNC('month', MAX(date)) AS max_date
	FROM flights
),

all_dates AS (
	SELECT
		GENERATE_SERIES(min_date::date, max_date::date, '1 day') AS date
	FROM date_range
),

dates_launches_cross AS (
	SELECT
		all_dates.date,
		launches.name AS launch
	FROM all_dates
	CROSS JOIN launches
),

aggregated_flights AS (
	SELECT
		date,
		launch,
		1 AS flight_registered,
		MAX(points) AS max_points,
		MAX(length) AS max_length
	FROM flights
	GROUP BY 1, 2
),

daily_aggregated_flights AS (
	SELECT
		dates_launches_cross.date,
		dates_launches_cross.launch,
		COALESCE(flight_registered, 0) AS flight_registered,
		COALESCE(max_points, 0) AS max_points,
		COALESCE(max_length, 0) AS max_length
	FROM dates_launches_cross
	LEFT JOIN aggregated_flights
	ON dates_launches_cross.date = aggregated_flights.date
	AND dates_launches_cross.launch = aggregated_flights.launch
)

SELECT * FROM daily_aggregated_flights