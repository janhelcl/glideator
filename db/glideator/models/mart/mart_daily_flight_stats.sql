WITH flights AS (
	SELECT * FROM {{ ref('fact_flights')}}
),

sites AS (
	SELECT * FROM {{ ref('dim_sites')}}
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

dates_sites_cross AS (
	SELECT
		all_dates.date,
		sites.site_id,
		sites.name,
		sites.xc_name AS site
	FROM all_dates
	CROSS JOIN sites
),

aggregated_flights AS (
	SELECT
		date,
		site,
		COUNT(*) AS flight_cnt,
		MAX(points) AS max_points,
		MAX(length) AS max_length
	FROM flights
	GROUP BY 1, 2
),

daily_aggregated_flights AS (
	SELECT
		dates_sites_cross.date,
		dates_sites_cross.site_id,
		dates_sites_cross.name AS site,
		CASE WHEN flight_cnt > 0 THEN 1 ELSE 0 END AS flight_registered,
		COALESCE(flight_cnt, 0) AS flight_cnt,
		COALESCE(max_points, 0) AS max_points,
		COALESCE(max_length, 0) AS max_length
	FROM dates_sites_cross
	LEFT JOIN aggregated_flights
	ON dates_sites_cross.date = aggregated_flights.date
	AND dates_sites_cross.site = aggregated_flights.site
)

SELECT * FROM daily_aggregated_flights