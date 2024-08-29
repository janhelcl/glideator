WITH mapping AS (
	SELECT * FROM {{ ref('seed_launch_mapping')}}
),

launches AS (
	SELECT * FROM {{ ref('stg_launches')}}
),

mapped_and_filtered AS (
	SELECT
		mapping.xcontest_name AS name,
		launches.longitude,
		launches.latitude,
		launches.altitude,
		launches.superelevation
	FROM launches
	INNER JOIN mapping
	ON launches.name = mapping.pgmap_name
),

aggregated AS (
	SELECT
		name,
		MAX(longitude) AS longitude,
		MAX(latitude) AS latitude,
		MAX(altitude) AS altitude,
		MAX(superelevation) AS superelevation
	FROM mapped_and_filtered
	GROUP BY 1
)

SELECT * FROM aggregated