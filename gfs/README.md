
# GFS Data Fetcher

A Python package for downloading and processing Global Forecast System (GFS) historical and forecast data. This tool simplifies accessing, mapping, and organizing GFS data for various atmospheric variables.

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
  - [Fetching Historical Data](#fetching-historical-data)
  - [Fetching Forecast Data](#fetching-forecast-data)
- [Schema](#schema)
- [Utilities](#utilities)

## Features

- **Data Retrieval**: Easily download GFS historical and forecast data.
- **Variable Mapping**: Map forecast and historical variable names using a predefined schema.
- **Data Processing**: Flatten and organize data columns for seamless integration.
- **Utility Functions**: Tools for rounding coordinates and handling latitude/longitude values.

## Installation

Ensure you have [Poetry](https://python-poetry.org/) installed. Then, clone the repository and install the dependencies:

```bash
git clone https://github.com/janhelcl/glideator.git
cd gfs
poetry install
```

## Configuration

Update the `pyproject.toml` with your project details if necessary. The `schema.json` defines the mapping between forecast and historical variable names and their positions.

## Usage

### Fetching Historical Data

```python
from datetime import datetime
from gfs.fetch import get_gfs_data

# Define parameters
date = datetime(2023, 10, 1)
run = 0  # GFS run number (e.g., 0, 6, 12, 18)
delta = 24  # Forecast hour
lat_gfs = [40.0, 41.0, 42.0]  # List of latitudes
lon_gfs = [-105.0, -104.0, -103.0]  # List of longitudes

# Fetch historical data
historical_data = get_gfs_data(date, run, delta, lat_gfs, lon_gfs, source='hist')
print(historical_data.head())
```

### Fetching Forecast Data

```python
from datetime import datetime
from gfs.fetch import get_gfs_data

# Define parameters
date = datetime(2023, 10, 1)
run = 0  # GFS run number
delta = 24  # Forecast hour
lat_gfs = [40.0, 41.0, 42.0]
lon_gfs = [-105.0, -104.0, -103.0]

# Fetch forecast data
forecast_data = get_gfs_data(date, run, delta, lat_gfs, lon_gfs, source='forecast')
print(forecast_data.head())
```

## Schema

The `schema.json` file maps the GFS variable names used in forecast and historical data to standardized keys used within the application. Each entry includes:

- `forecast_name`: The variable name in the forecast dataset.
- `hist_name`: The variable name in the historical dataset.
- `position`: The position index for ordering.

Example entry:

```json
{
    "u_wind_500hpa_ms": {
        "forecast_name": "ugrdprs_500",
        "hist_name": "u-component_of_wind_isobaric_50000",
        "position": 0
    }
}
```

## Utilities

Utility functions are available in `gfs/utils.py` to assist with data processing:

- **Rounding Coordinates**: Round latitude and longitude values to the nearest quarter degree.

```python
from gfs.utils import gfs_lat, gfs_lon

rounded_lat = gfs_lat(40.123)
rounded_lon = gfs_lon(-104.567)
print(rounded_lat, rounded_lon)  # Output: 40.0, 255.5
```