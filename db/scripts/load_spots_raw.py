"""
Load paragliding spot data from CSV files into a PostgreSQL database.

This script reads CSV files containing paragliding spot information and inserts the data into a PostgreSQL database.
It handles duplicate entries based on a unique identifier and logs any errors encountered during the process.

Usage:
    python load_spots.py <input_csv_file> [--log_file <output_log_file>]

Arguments:
    input_csv_file: Path to the input CSV file containing paragliding spot data.

Options:
    --log_file <output_log_file>: (Optional) Path to the log file where processing information and errors will be recorded.
                                  If not provided, logging will default to the console.

Example:
    python load_spots.py spots.csv
    python load_spots.py spots.csv --log_file load_spots.log
"""

import os
import csv
import sys
import argparse
import logging
from dotenv import load_dotenv
import psycopg2
from psycopg2 import sql, extras

# Constants
SCHEMA = 'source'
TABLE = 'spots_raw'

def setup_logging(log_file=None):
    """
    Configures the logging settings.

    Args:
        log_file (str, optional): Path to the log file. If provided, logs will be written to this file in addition to the console.
    """
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    
    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    
    # File handler (if log_file is provided)
    if log_file:
        fh = logging.FileHandler(log_file)
        fh.setLevel(logging.INFO)
        fh.setFormatter(formatter)
        logger.addHandler(fh)

def load_data_to_db(csv_file, db_config):
    """
    Loads data from a CSV file into the PostgreSQL database.

    Args:
        csv_file (str): Path to the input CSV file.
        db_config (dict): Database configuration parameters.
    """
    try:
        conn = psycopg2.connect(
            dbname=db_config['dbname'],
            user=db_config['user'],
            password=db_config['password'],
            host=db_config['host'],
            port=db_config['port']
        )
        cursor = conn.cursor()
        logging.info("Connected to the PostgreSQL database successfully.")
    except Exception as e:
        logging.error(f"Failed to connect to the database: {e}")
        sys.exit(1)

    # Create schema and table if they don't exist
    try:
        create_table_query = sql.SQL(f"""
            CREATE SCHEMA IF NOT EXISTS {SCHEMA};
            
            CREATE TABLE IF NOT EXISTS {SCHEMA}.{TABLE} (
                spot_id SERIAL PRIMARY KEY,
                full_name TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                latitude FLOAT,
                longitude FLOAT,
                spot_type VARCHAR(50),
                takeoff_type VARCHAR(50),
                hg BOOLEAN,
                wind_direction VARCHAR(50),
                altitude INTEGER,
                UNIQUE(full_name, latitude, longitude)  -- Assuming combination as unique identifier
            );
        """)
        cursor.execute(create_table_query)
        conn.commit()
        logging.info(f"Schema '{SCHEMA}' and table '{TABLE}' are ready.")
    except Exception as e:
        logging.error(f"Error creating schema/table: {e}")
        conn.rollback()
        cursor.close()
        conn.close()
        sys.exit(1)

    # Read CSV and prepare data for insertion
    data_to_insert = []
    errors = []
    rows_processed = 0

    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row_number, row in enumerate(reader, start=2):  # Starting at 2 to account for header
                try:
                    # Extract and clean data
                    full_name = row['full_name'].strip()
                    name = row['name'].strip()
                    description = row['description'].strip()
                    latitude = float(row['latitude']) if row['latitude'] else None
                    longitude = float(row['longitude']) if row['longitude'] else None
                    spot_type = row['spot_type'].strip() if row['spot_type'] else None
                    takeoff_type = row['takeoff_type'].strip() if row['takeoff_type'] else None
                    hg = row['hg'].strip().lower() == 'true' if row['hg'] else False
                    wind_direction = row['wind_direction'].strip() if row['wind_direction'] else None
                    altitude = int(row['altitude']) if row['altitude'] else None

                    data_to_insert.append((
                        full_name,
                        name,
                        description,
                        latitude,
                        longitude,
                        spot_type,
                        takeoff_type,
                        hg,
                        wind_direction,
                        altitude
                    ))
                    rows_processed += 1
                except Exception as e:
                    error_info = {
                        'row_number': row_number,
                        'error': f"Data parsing error: {str(e)}"
                    }
                    errors.append(error_info)
                    logging.error(f"Row {row_number}: Data parsing error: {e}")
    except FileNotFoundError:
        logging.error(f"CSV file '{csv_file}' not found.")
        cursor.close()
        conn.close()
        sys.exit(1)
    except Exception as e:
        logging.error(f"Error reading CSV file: {e}")
        cursor.close()
        conn.close()
        sys.exit(1)

    # Insert data into the database
    try:
        insert_query = sql.SQL(f"""
            INSERT INTO {SCHEMA}.{TABLE} (
                full_name, name, description, latitude, longitude, 
                spot_type, takeoff_type, hg, wind_direction, altitude
            ) VALUES %s
            ON CONFLICT (full_name, latitude, longitude) DO NOTHING;
        """)
        extras.execute_values(
            cursor, insert_query.as_string(conn), data_to_insert, template=None, page_size=100
        )
        conn.commit()
        logging.info(f"Processed {rows_processed} rows from CSV file.")
    except Exception as e:
        logging.error(f"Error inserting data into the database: {e}")
        conn.rollback()
        cursor.close()
        conn.close()
        sys.exit(1)

    cursor.close()
    conn.close()
    logging.info("Database connection closed.")

    # Log errors
    if errors:
        logging.error("\nSummary of all errors encountered during CSV parsing:")
        for error in errors:
            logging.error(f"Row {error['row_number']}: {error['error']}")

def main():
    """
    Main function to parse arguments and initiate the data loading process.
    """
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('input_csv_file', type=str, help='Path to the input CSV file containing paragliding spot data')
    parser.add_argument('--log_file', type=str, help='(Optional) Path to the log file for recording processing details and errors')
    args = parser.parse_args()

    # Set up logging
    setup_logging(args.log_file)

    # Load environment variables from .env file
    load_dotenv()

    # Database configuration from environment variables
    db_config = {
        'dbname': os.getenv('DB_NAME'),
        'user': os.getenv('DB_USER'),
        'password': os.getenv('DB_PASSWORD'),
        'host': os.getenv('DB_HOST'),
        'port': os.getenv('DB_PORT')
    }

    # Validate database configuration
    missing_params = [key for key, value in db_config.items() if not value]
    if missing_params:
        logging.error(f"Missing database configuration parameters: {', '.join(missing_params)}")
        sys.exit(1)

    # Load data to DB
    load_data_to_db(args.input_csv_file, db_config)

if __name__ == "__main__":
    main()