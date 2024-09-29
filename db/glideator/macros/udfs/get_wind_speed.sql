{% macro create_get_wind_speed_function() %}
CREATE OR REPLACE FUNCTION glideator.get_wind_speed(
    u_component numeric,
    v_component numeric
)
RETURNS numeric AS $$
DECLARE
    wind_speed numeric;
BEGIN
    wind_speed := SQRT(POWER(u_component, 2) + POWER(v_component, 2));
    RETURN wind_speed;
END;
$$ LANGUAGE plpgsql;
{% endmacro %}
