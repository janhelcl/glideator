{% macro create_udfs() %}

{{ create_bin_wind_direction_function() }}
{{ create_get_wind_direction_function() }}
{{ create_get_wind_speed_function() }}
{{ create_get_gfs_coordinates_function() }}

{% endmacro %}