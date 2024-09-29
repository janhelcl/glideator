{% macro create_get_gfs_coordinates_function() %}
CREATE OR REPLACE FUNCTION glideator.get_gfs_coords(
    latitude numeric,
    longitude numeric,
    step numeric DEFAULT 0.25
)
RETURNS numeric[] AS $$
DECLARE
    gfs_lat_step numeric := step;
    gfs_lon_step numeric := step;
    gfs_lat numeric;
    gfs_lon numeric;
BEGIN
    gfs_lat := ROUND(latitude / gfs_lat_step) * gfs_lat_step;
    gfs_lon := ROUND(longitude / gfs_lon_step) * gfs_lon_step;
    
    -- Ensure longitude is within -180 to 180 range
    IF gfs_lon > 180 THEN
        gfs_lon := gfs_lon - 360;
    ELSIF gfs_lon < -180 THEN
        gfs_lon := gfs_lon + 360;
    END IF;
    
    RETURN ARRAY[gfs_lat, gfs_lon];
END;
$$ LANGUAGE plpgsql;
{% endmacro %}

