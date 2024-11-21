"""
Load flight data from JSONL files into a PostgreSQL database.
"""
import os
import glob
import json
import argparse
import logging

from dotenv import load_dotenv
import psycopg2
from psycopg2 import sql


FILE_PATTERN = 'flights_*.jsonl'
SCHEMA = 'source'
TABLE = 'flights'


def load_data_to_db(folder_path, db_config):
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    conn = psycopg2.connect(
        dbname=db_config['dbname'],
        user=db_config['user'],
        password=db_config['password'],
        host=db_config['host'],
        port=db_config['port']
    )
    cursor = conn.cursor()

    file_pattern = os.path.join(folder_path, FILE_PATTERN)
    files = glob.glob(file_pattern)
    
    create_query = f"""
        CREATE SCHEMA IF NOT EXISTS {SCHEMA};
        CREATE TABLE IF NOT EXISTS {SCHEMA}.{TABLE} (
            date DATE NOT NULL,
            start_time TIME NOT NULL,
            pilot VARCHAR(255) NOT NULL,
            launch VARCHAR(255),
            type CHAR(2) NOT NULL,
            length NUMERIC(5, 2) NOT NULL,
            points NUMERIC(5, 2) NOT NULL,
            glider_cat CHAR(2) NOT NULL,
            glider VARCHAR(255) NOT NULL,
            flight_id INTEGER PRIMARY KEY,
            latitude FLOAT,
            longitude FLOAT,
            country VARCHAR(255)
            ); 
        """
    cursor.execute(create_query)
    conn.commit()
    
    seen_flight_ids = set()  # Initialize a set to track seen flight_ids

    errors = []  # List to collect errors
    for file in files:
        rows_processed = 0
        with open(file, 'r', encoding='utf-8') as f:
            for line in f:
                data = json.loads(line.strip())
                
                # Fix typo in crawlers:
                if 'lenght' in data:
                    data['length'] = data['lenght']
                if 'latitutde' in data:
                    data['latitude'] = data['latitutde']
                
                flight_id = data.get('flight_id')
                if flight_id is None:
                    logging.warning(f'Flight ID missing in data: {data}')
                    continue  # Skip entries without flight_id

                if flight_id in seen_flight_ids:
                    logging.info(f'Duplicate flight_id {flight_id} found. Skipping entry.')
                    continue  # Skip duplicate entries
                seen_flight_ids.add(flight_id)  # Mark flight_id as seen

                insert_query = sql.SQL(f"""
                    INSERT INTO {SCHEMA}.{TABLE} (
                        date, start_time, pilot, launch, type, length, points, 
                        glider_cat, glider, flight_id, latitude, longitude, country
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """)
                try:
                    cursor.execute(insert_query, (
                        data['date'],
                        data['start_time'],
                        data['pilot'],
                        data['launch'],
                        data['type'],
                        data['length'],
                        data['points'],
                        data['glider_cat'],
                        data['glider'],
                        flight_id,
                        data.get('latitude'),
                        data.get('longitude'),
                        data.get('country')
                    ))
                    rows_processed += 1
                except psycopg2.IntegrityError as e:
                    error_info = {
                        'date': data['date'],
                        'flight_id': flight_id,
                        'error': f'Integrity error: {str(e)}'
                    }
                    errors.append(error_info)
                    logging.error(f'Integrity error for flight_id {flight_id}: {e}')
                    conn.rollback()
                    continue  # Skip entries that cause integrity errors
                except Exception as e:
                    error_info = {
                        'date': data['date'],
                        'flight_id': flight_id,
                        'error': str(e)
                    }
                    errors.append(error_info)
                    logging.error(f'Error processing flight_id {flight_id}: {e}')
                    conn.rollback()
                    continue  # Skip entries that cause other errors

            conn.commit()
            logging.info(f'Processed {rows_processed} unique rows from file: {file}')

    # Print collected errors at the end
    if errors:
        logging.error("\nSummary of all errors encountered:")
        for error in errors:
            logging.error(f"Date: {error['date']}, Flight ID: {error['flight_id']}, Error: {error['error']}")

    cursor.close()
    conn.close()


if __name__ == "__main__":
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder_path', type=str, help='Path to the folder containing JSONL files')
    args = parser.parse_args()
    db_config = {
        'dbname': os.getenv('DB_NAME'),
        'user': os.getenv('DB_USER'),
        'password': os.getenv('DB_PASSWORD'),
        'host': os.getenv('DB_HOST'),
        'port': os.getenv('DB_PORT')
    }
    load_data_to_db(args.folder_path, db_config)
