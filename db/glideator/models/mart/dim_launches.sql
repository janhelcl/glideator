WITH mapping AS (
	SELECT * FROM {{ ref('seed_launch_mapping')}}
),

launches AS (
	SELECT * FROM {{ ref('stg_launches')}}
),

mapped_and_filtered AS (
	SELECT
		xcontest_name AS name,
		pgmap_name,
		longitude,
		latitude,
		altitude,
		superelevation,
		ARRAY[wind_usable_from, wind_usable_to] AS usable_wind_range,
		ARRAY[wind_optimal_from, wind_optimal_to] AS optimal_wind_range,
		ROW_NUMBER() OVER (PARTITION BY xcontest_name ORDER BY pgmap_name) AS row_num
	FROM launches
	INNER JOIN mapping
	ON launches.name = mapping.pgmap_name
),

aggregated AS (
	SELECT
		name,
		AVG(longitude) AS longitude,
		AVG(latitude) AS latitude,
		MAX(altitude) AS altitude,
		MAX(superelevation) AS superelevation,
		MAX(CASE WHEN row_num = 1 THEN pgmap_name END) AS name1,
		MAX(CASE WHEN row_num = 1 THEN usable_wind_range END) AS usable_wind_range1,
		MAX(CASE WHEN row_num = 1 THEN optimal_wind_range END) AS optimal_wind_range1,
		MAX(CASE WHEN row_num = 2 THEN pgmap_name END) AS name2,
		MAX(CASE WHEN row_num = 2 THEN usable_wind_range END) AS usable_wind_range2,
		MAX(CASE WHEN row_num = 2 THEN optimal_wind_range END) AS optimal_wind_range2
	FROM mapped_and_filtered
	GROUP BY 1
)

SELECT * FROM aggregated