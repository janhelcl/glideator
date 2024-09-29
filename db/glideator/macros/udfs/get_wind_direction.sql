{% macro create_get_wind_direction_function() %}
CREATE OR REPLACE FUNCTION glideator.get_wind_direction(
    u_component numeric,
    v_component numeric
)
RETURNS numeric AS $$
DECLARE
    wind_direction numeric;
BEGIN
    wind_direction := 180 + (180 / PI()) * ATAN2(u_component, v_component);
    wind_direction := wind_direction - FLOOR(wind_direction / 360) * 360;
    RETURN wind_direction;
END;
$$ LANGUAGE plpgsql;
{% endmacro %}
