# Glideator dbt Project

This directory contains the dbt (data build tool) project for managing the analytics database of the Glideator platform - a machine learning-powered paragliding weather forecasting system.

## Overview

This dbt project transforms raw flight data scraped from XContest and launch site data from the Paragliding Map API into a clean, analytics-ready format. The pipeline creates fact and dimension tables that feed into machine learning models for predicting paragliding conditions.

## Project Structure

### Configuration
- **`dbt_project.yml`**: Main configuration file defining the project structure and materialization strategies
- **`profiles.yml`**: Database connection configuration using environment variables for PostgreSQL
- **`.user.yml`**: User-specific settings (automatically generated)

### Data Models

#### Staging (`models/stage/`)
- **`flights/`**: Raw flight data from XContest, filtered to exclude hang gliders and unknown launches
  - `stg_flights.sql`: Cleans and standardizes flight data (coordinates, site names, etc.)
  - `_flights_sources.yml`: Source configuration for the flights table
- **`launches/`**: Launch site data from the Paragliding Map API
  - `stg_launches.sql`: Transforms launch site data including wind conditions and activity status
  - `_launches_sources.yml`: Source configuration for the launches table

#### Mart (`models/mart/`)
- **`dim_sites.sql`**: Dimension table of launch sites with GFS weather grid coordinates
- **`dim_launches.sql`**: Dimension table of launch sites with detailed metadata
- **`fact_flights.sql`**: Core fact table containing all flight data joined with site information
- **`mart_daily_flight_stats.sql`**: Daily aggregated flight statistics by site for ML model training

### Seeds (`seeds/`)
- **`seed_sites.csv`**: Master reference data for launch sites with coordinates and metadata
- **`seed_launch_mapping.csv`**: Mapping between different site naming conventions
- **`seed_sites_old.csv`**: Legacy site data for backward compatibility

### Macros (`macros/`)
- **`create_udfs.sql`**: Main macro that creates all user-defined functions
- **`udfs/`**: PostgreSQL user-defined functions for weather data processing:
  - `get_gfs_coordinates.sql`: Maps site coordinates to GFS weather grid points
  - `get_wind_direction.sql`: Calculates wind direction from components
  - `get_wind_speed.sql`: Calculates wind speed from components
  - `bin_wind_direction.sql`: Bins wind direction into categorical ranges

### Data Flow

1. **Raw Data**: Flight data from XContest and launch site data from Paragliding Map API
2. **Staging**: Clean and standardize data formats, filter out invalid records
3. **Mart**: Create dimensional model with sites, launches, and flight facts
4. **Aggregation**: Generate daily statistics for ML model training

### Schema Configuration

The project uses a multi-schema approach:
- `source`: Raw data tables
- `stage`: Staging models (views)
- `mart`: Final dimensional models (views)
- `glideator`: Main application schema

## Dependencies

```text
dbt-core              # Core dbt functionality
dbt-postgres          # PostgreSQL adapter
psycopg2-binary       # PostgreSQL Python driver
python-dotenv         # Environment variable management
xarray                # N-dimensional data processing
sqlalchemy            # SQL toolkit
fastkml/lxml/pykml    # KML/KMZ file processing
bs4                   # HTML/XML parsing
```

## Environment Setup

1. **Install dependencies**:
   ```bash
   pip install -r db_requirements.txt
   ```

2. **Set environment variables**:
   ```bash
   export DB_HOST=localhost
   export DB_USER=postgres
   export DB_PASSWORD=your_password
   export DB_NAME=glideator
   export DB_PORT=5432
   ```

3. **Initialize database schema**:
   The project automatically creates the `glideator` schema and required UDFs on first run.

## Usage

Navigate to the `db/glideator` directory and run:

### Basic Commands
```bash
# Install dependencies and compile project
dbt deps
dbt compile

# Run all models
dbt run

# Run tests
dbt test

# Build everything (run + test)
dbt build

# Generate documentation
dbt docs generate
dbt docs serve
```

### Development Commands
```bash
# Run specific models
dbt run --select stg_flights
dbt run --select mart.fact_flights

# Run models downstream from a specific model
dbt run --select +fact_flights

# Test specific models
dbt test --select dim_sites
```

## Data Quality

The project includes:
- Source data validation through schema definitions
- Geospatial filtering to remove flights too far from registered launch sites
- Site name normalization to handle inconsistencies between data sources
- Automatic UDF creation for weather data processing

## Integration with ML Pipeline

The mart models feed directly into the Glideator ML pipeline:
- `fact_flights` provides historical flight data for training
- `dim_sites` provides launch site metadata and GFS coordinates
- `mart_daily_flight_stats` provides aggregated features for model training

## Materialization Strategy

- **Staging models**: Materialized as views for real-time data access
- **Mart models**: Materialized as views for flexibility and storage efficiency
- **Seeds**: Static reference data loaded as tables