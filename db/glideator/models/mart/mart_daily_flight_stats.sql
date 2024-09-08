WITH flights AS (
	SELECT * FROM {{ ref('fact_flights')}}
),

launches AS (
	SELECT * FROM {{ ref('dim_launches')}}
),

date_range AS (
	SELECT
		DATE(MIN(date)) AS min_date,
		DATE(MAX(date)) AS max_date
	FROM flights
),

all_dates AS (
	SELECT
		DATE(GENERATE_SERIES(min_date::date, max_date::date, '1 day')) AS date
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
		COUNT(*) AS flight_cnt,
		MAX(points) AS max_points,
		MAX(length) AS max_length
	FROM flights
	GROUP BY 1, 2
),

daily_aggregated_flights AS (
	SELECT
		dates_launches_cross.date,
		dates_launches_cross.launch,
		CASE WHEN flight_cnt > 0 THEN 1 ELSE 0 END AS flight_registered,
		COALESCE(flight_cnt, 0) AS flight_cnt,
		COALESCE(max_points, 0) AS max_points,
		COALESCE(max_length, 0) AS max_length
	FROM dates_launches_cross
	LEFT JOIN aggregated_flights
	ON dates_launches_cross.date = aggregated_flights.date
	AND dates_launches_cross.launch = aggregated_flights.launch
)

SELECT * FROM daily_aggregated_flights