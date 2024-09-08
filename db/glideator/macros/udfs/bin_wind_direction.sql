{% macro create_bin_wind_direction_function() %}
CREATE OR REPLACE FUNCTION glideator.bin_wind_direction(
	wind_direction numeric,
	bin_size integer DEFAULT 5
)
RETURNS numeric AS $$
DECLARE
	bin_mid numeric;
BEGIN
	bin_mid := FLOOR(wind_direction / bin_size) * bin_size + (bin_size / 2.0);
	IF wind_direction = 360 THEN
		bin_mid := bin_size / 2.0;
	END IF;
	RETURN bin_mid;
END;
$$ LANGUAGE plpgsql;
{% endmacro %}