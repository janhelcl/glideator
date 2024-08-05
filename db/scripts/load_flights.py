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

    for file in files:
        rows_processed = 0
        with open(file, 'r', encoding='utf-8') as f:
            for line in f:
                data = json.loads(line.strip())
                
                #fix typo in crawlers:
                if 'lenght' in data:
                    data['length'] = data['lenght']
                
                insert_query = sql.SQL("""
                    INSERT INTO flights_raw (date, start_time, pilot, launch, type, length, points, glider_cat, glider, flight_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """)
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
                    data['flight_id']
                ))
                rows_processed += 1
            conn.commit()
            logging.info(f'Processed {rows_processed} rows from file: {file}')
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
