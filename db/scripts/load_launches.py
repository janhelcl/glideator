"""
This script is responsible for loading paragliding launch site data from the "Startovacky" API into a PostgreSQL database.

Key features:
1. Fetches launch site data for the Czech Republic from the paragliding-mapa.cz API.
2. Processes and transforms the API response data.
3. Loads the processed data into a specified PostgreSQL database table.

The script uses the following main components:
- requests: For making HTTP requests to the API.
- psycopg2: For PostgreSQL database operations.
- dotenv: For loading environment variables.

Usage:
This script is typically run as part of a data pipeline to update paragliding launch site information.
It requires proper environment setup, including database credentials stored in a .env file.
"""
import os
import logging
import requests
from datetime import datetime

import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv


SCHEMA = 'source'
TABLE = 'launches'
API_URL = 'https://www.paragliding-mapa.cz/api/v0.1/launch?country=cz'


def fetch_data():
    """
    Fetch data from the API.

    Returns:
        list: A list of launch data from the API response.
    """
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logging.info(f"Fetching data from API: {API_URL}")
    response = requests.get(API_URL)
    if response.status_code != 200:
        logging.error(f"Failed to fetch data from API. Status code: {response.status_code}")
        return []
    return response.json().get("data", [])


def load_data_to_db(launches, db_config):
    """
    Load data into the database.

    Args:
        launches (list): A list of launch data to be loaded.
        db_config (dict): Database configuration parameters.
    """
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    conn = psycopg2.connect(
        dbname=db_config['dbname'],
        user=db_config['user'],
        password=db_config['password'],
        host=db_config['host'],
        port=db_config['port']
    )
    cursor = conn.cursor()
    
    create_query = f"""
        CREATE SCHEMA IF NOT EXISTS {SCHEMA};
        CREATE TABLE IF NOT EXISTS {SCHEMA}.{TABLE} (
            id INTEGER PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            latitude DOUBLE PRECISION NOT NULL,
            longitude DOUBLE PRECISION NOT NULL,
            altitude INTEGER,
            superelevation INTEGER,
            wind_usable_from INTEGER,
            wind_usable_to INTEGER,
            wind_optimal_from INTEGER,
            wind_optimal_to INTEGER,
            flying_status INTEGER,
            active BOOLEAN,
            loaded_dttm TIMESTAMPTZ
            ); 
        """
    cursor.execute(create_query)
    conn.commit()
    
    current_time = datetime.utcnow()
    rows_processed = 0
    for launch in launches:
        insert_query = sql.SQL(f"""
            INSERT INTO {SCHEMA}.{TABLE} (id, name, latitude, longitude, altitude, superelevation, wind_usable_from, 
                                          wind_usable_to, wind_optimal_from, wind_optimal_to, flying_status, active, loaded_dttm)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """)
        cursor.execute(insert_query, (
            launch['id'],
            launch['name'],
            launch['latitude'],
            launch['longitude'],
            launch['altitude'],
            launch['superelevation'],
            launch['wind_usable_from'],
            launch['wind_usable_to'],
            launch['wind_optimal_from'],
            launch['wind_optimal_to'],
            launch['flying_status'],
            launch['active'],
            current_time
        ))
        rows_processed += 1
    logging.info(f'Processed {rows_processed} rows from API: {API_URL}')
    conn.commit()
    cursor.close()
    conn.close()


def main():
    """
    Main function to fetch launch data from an API and load it into a database.

    This function performs the following steps:
    1. Loads environment variables from a .env file.
    2. Configures the database connection using environment variables.
    3. Fetches launch data from an external API.
    4. Loads the fetched data into the specified database table.

    The function relies on the following environment variables:
    - DB_NAME: The name of the database
    - DB_USER: The username for database access
    - DB_PASSWORD: The password for database access
    - DB_HOST: The host address of the database
    - DB_PORT: The port number for the database connection

    Note: This function assumes that the fetch_data() and load_data_to_db() 
    functions are defined elsewhere in the script.
    """
    load_dotenv()
    db_config = {
        'dbname': os.getenv('DB_NAME'),
        'user': os.getenv('DB_USER'),
        'password': os.getenv('DB_PASSWORD'),
        'host': os.getenv('DB_HOST'),
        'port': os.getenv('DB_PORT')
    }
    launches = fetch_data()
    load_data_to_db(launches, db_config)

if __name__ == "__main__":
    main()
