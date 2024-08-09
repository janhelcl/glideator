"""
Loads launches data from a JSONL file into a PostgreSQL database.
"""
import os
import json
import logging
import requests

import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv


SCHEMA = 'source'
TABLE = 'launches'
API_URL = 'https://www.paragliding-mapa.cz/api/v0.1/launch?country=cz'


def fetch_data():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logging.info(f"Fetching data from API: {API_URL}")
    response = requests.get(API_URL)
    if response.status_code != 200:
        logging.error(f"Failed to fetch data from API. Status code: {response.status_code}")
        return []
    return response.json().get("data", [])


def load_data_to_db(launches, db_config):
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
            active BOOLEAN
            ); 
        """
    cursor.execute(create_query)
    conn.commit()

    rows_processed = 0
    for launch in launches:
        insert_query = sql.SQL(f"""
            INSERT INTO {SCHEMA}.{TABLE} (id, name, latitude, longitude, altitude, superelevation, wind_usable_from, 
                                          wind_usable_to, wind_optimal_from, wind_optimal_to, flying_status, active)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """)
        cursor.execute(insert_query, (
            launch['id'],
            launch['name'],
            launch['latitude'],
            launch['latitude'],
            launch['altitude'],
            launch['superelevation'],
            launch['wind_usable_from'],
            launch['wind_usable_to'],
            launch['wind_optimal_from'],
            launch['wind_optimal_to'],
            launch['flying_status'],
            launch['active'],
        ))
        rows_processed += 1
    logging.info(f'Processed {rows_processed} rows from API: {API_URL}')
    conn.commit()
    cursor.close()
    conn.close()

if __name__ == "__main__":
    load_dotenv()
    db_config = {
        'dbname': os.getenv('DB_NAME'),
        'user': os.getenv('DB_USER'),
        'password': os.getenv('DB_PASSWORD'),
        'host': os.getenv('DB_HOST'),
        'port': os.getenv('DB_PORT')
    }
    launches = fetch_data()
    # print(launches[0])
    load_data_to_db(launches, db_config)
