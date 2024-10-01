import os
import json
import numpy as np

# sources
GFS_HIST_BASE = "https://thredds.rda.ucar.edu/thredds/dodsC/files/g/d084001"
GFS_FORECAST_BASE = "https://nomads.ncep.noaa.gov/dods"

# levels
PA_LVLS = [50000, 55000,60000, 65000, 70000, 75000, 80000, 85000,90000, 92500, 95000, 97500, 100000]
HPA_LVLS = np.array(PA_LVLS) / 100
WIND_AGL_LVLS = [10., 100.]
TEMP_AGL_LVLS = [2., 80., 100.]
DEWPOINT_AGL_LVLS = [2.]

# variables
VARIABLES_HIST = {
    # wind
    'u-component_of_wind_isobaric': PA_LVLS, 
    'v-component_of_wind_isobaric': PA_LVLS,
    'u-component_of_wind_height_above_ground': WIND_AGL_LVLS,
    'v-component_of_wind_height_above_ground': WIND_AGL_LVLS,
    'Wind_speed_gust_surface': None,
    #temperature
    'Temperature_isobaric': PA_LVLS,
    'Temperature_height_above_ground': TEMP_AGL_LVLS,
    'Dewpoint_temperature_height_above_ground': DEWPOINT_AGL_LVLS,
    #pressure
    'Pressure_surface': None,
    #humidity
    'Precipitable_water_entire_atmosphere_single_layer': None,
    'Relative_humidity_isobaric': PA_LVLS,
    #geopotential
    'Geopotential_height_isobaric': PA_LVLS,
    'Geopotential_height_surface': None
}

VARIABLES_FORECAST = [
    #wind
    'ugrdprs',
    'vgrdprs',
    'ugrd10m',
    'vgrd10m',
    'ugrd100m',
    'vgrd100m',
    'gustsfc',
    #temperature
    'tmpprs',
    'tmp2m',
    'tmp80m',
    'tmp100m',
    'dpt2m',
    #pressure
    'pressfc',
    #humidity
    'pwatclm',
    'rhprs',
    #geopotential
    'hgtprs',
    'hgtsfc'
]


current_dir = os.path.dirname(os.path.abspath(__file__))
schema_path = os.path.join(current_dir, 'schema.json')
SCHEMA = json.load(open(schema_path))