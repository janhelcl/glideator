#!/usr/bin/env python3
"""
Helper script to load TSV data into production database (Render).
Reads DATABASE_URL from .env file and handles encoding properly.
"""

import sys
import subprocess
import os
from pathlib import Path

try:
    import psycopg2
    from psycopg2.extras import execute_values
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

def load_env_file(env_path):
    """Load environment variables from .env file."""
    if not env_path.exists():
        return
    
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()

def load_to_production_psycopg2(jsonl_path, database_url):
    """Load using psycopg2 COPY FROM with batching."""
    from jsonl_to_tsv import to_pg_array
    import json
    import io
    import tempfile
    
    print(f"Starting conversion and load from {jsonl_path}...")
    print(f"Connecting to production database via psycopg2...")
    print("This may take several minutes...")
    
    # Connect to database
    conn = psycopg2.connect(database_url)
    cur = conn.cursor()
    
    input_file = open(jsonl_path, "r", encoding="utf-8")
    line_count = 0
    batch_size = 50000  # Load in batches of 50k rows
    
    # Use temp file for better memory efficiency with large files
    with tempfile.NamedTemporaryFile(mode='w+', encoding='utf-8', delete=False, suffix='.tsv') as temp_file:
        temp_path = temp_file.name
        
        try:
            # Convert and write to temp file
            for line_num, line in enumerate(input_file, 1):
                line = line.strip()
                if not line:
                    continue
                
                try:
                    obj = json.loads(line)
                    site_id = int(obj["site_id"])
                    date = str(obj["date"])
                    feats = obj["features"]
                    
                    if not isinstance(feats, list):
                        continue
                    
                    pg_array = to_pg_array(feats)
                    tsv_line = f"{site_id}\t{date}\t{pg_array}\n"
                    temp_file.write(tsv_line)
                    line_count += 1
                    
                    if line_count % batch_size == 0:
                        print(f"Processed {line_count} rows...", flush=True)
                        
                except Exception as e:
                    print(f"Error on line {line_num}: {e}", file=sys.stderr)
                    continue
        
        finally:
            input_file.close()
            temp_file.close()
        
        # Now load from temp file using COPY
        print(f"Loading {line_count} rows into database...")
        with open(temp_path, 'r', encoding='utf-8') as f:
            cur.copy_from(f, 'scaled_features', columns=('site_id', 'date', 'features'), sep='\t', null='NULL')
        
        conn.commit()
        print(f"\nSuccessfully loaded {line_count} rows!")
        
        # Clean up temp file
        os.unlink(temp_path)
    
    cur.close()
    conn.close()

def load_to_production_psql(jsonl_path, database_url):
    """Load using psql command (faster for large files)."""
    from jsonl_to_tsv import to_pg_array
    import json
    
    # Set up psql command
    psql_cmd = [
        "psql",
        database_url,
        "-c", r"\copy scaled_features (site_id, date, features) FROM STDIN WITH (FORMAT text, DELIMITER E'\t', NULL 'NULL');"
    ]
    
    print(f"Starting conversion and load from {jsonl_path}...")
    print(f"Connecting to production database via psql...")
    print("This may take several minutes...")
    
    # Open subprocess for psql
    proc = subprocess.Popen(
        psql_cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding='utf-8',
        bufsize=8192
    )
    
    # Stream convert and write to psql stdin
    input_file = open(jsonl_path, "r", encoding="utf-8")
    line_count = 0
    
    try:
        for line_num, line in enumerate(input_file, 1):
            line = line.strip()
            if not line:
                continue
            
            try:
                obj = json.loads(line)
                site_id = int(obj["site_id"])
                date = str(obj["date"])
                feats = obj["features"]
                
                if not isinstance(feats, list):
                    continue
                
                pg_array = to_pg_array(feats)
                tsv_line = f"{site_id}\t{date}\t{pg_array}\n"
                
                proc.stdin.write(tsv_line)
                line_count += 1
                
                if line_count % 10000 == 0:
                    print(f"Processed {line_count} rows...", flush=True)
                    
            except Exception as e:
                print(f"Error on line {line_num}: {e}", file=sys.stderr)
                continue
        
        # Close stdin to signal EOF
        proc.stdin.close()
        
        # Wait for completion
        stdout, stderr = proc.communicate()
        
        if proc.returncode != 0:
            print(f"Error during load: {stderr}", file=sys.stderr)
            sys.exit(proc.returncode)
        
        print(f"\nSuccessfully loaded {line_count} rows!")
        if stdout:
            print(stdout)
            
    finally:
        input_file.close()

def load_to_production(jsonl_path, database_url):
    """Load data, using psql if available, otherwise psycopg2."""
    # Check if psql is available
    psql_available = False
    try:
        result = subprocess.run(["psql", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            psql_available = True
    except FileNotFoundError:
        pass
    
    if psql_available:
        load_to_production_psql(jsonl_path, database_url)
    elif PSYCOPG2_AVAILABLE:
        load_to_production_psycopg2(jsonl_path, database_url)
    else:
        print("Error: Neither psql nor psycopg2 is available.", file=sys.stderr)
        print("\nPlease install one of:", file=sys.stderr)
        print("  1. PostgreSQL client (psql): https://www.postgresql.org/download/", file=sys.stderr)
        print("  2. psycopg2: pip install psycopg2-binary", file=sys.stderr)
        sys.exit(1)

def ensure_table_exists(database_url):
    """Ensure the scaled_features table exists."""
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS scaled_features (
        site_id integer NOT NULL,
        date date NOT NULL,
        features double precision[] NOT NULL,
        PRIMARY KEY (site_id, date)
    );
    CREATE INDEX IF NOT EXISTS idx_scaled_features_date ON scaled_features(date);
    """
    
    truncate_sql = "TRUNCATE TABLE scaled_features;"
    
    # Try psql first
    try:
        result = subprocess.run(["psql", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            psql_available = True
        else:
            psql_available = False
    except FileNotFoundError:
        psql_available = False
    
    if psql_available:
        print("Step 1: Ensuring table exists...")
        result1 = subprocess.run(
            ["psql", database_url, "-c", create_table_sql],
            capture_output=True,
            text=True
        )
        
        if result1.returncode != 0:
            print(f"Error creating table: {result1.stderr}", file=sys.stderr)
            sys.exit(1)
        
        print("Step 2: Truncating existing data...")
        result2 = subprocess.run(
            ["psql", database_url, "-c", truncate_sql],
            capture_output=True,
            text=True
        )
        
        if result2.returncode != 0:
            print(f"Error truncating table: {result2.stderr}", file=sys.stderr)
            sys.exit(1)
    elif PSYCOPG2_AVAILABLE:
        print("Step 1: Ensuring table exists...")
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        cur.execute(create_table_sql)
        conn.commit()
        
        print("Step 2: Truncating existing data...")
        cur.execute(truncate_sql)
        conn.commit()
        cur.close()
        conn.close()
    else:
        print("Error: Cannot connect to database. Need psql or psycopg2.", file=sys.stderr)
        sys.exit(1)
    
    print("Table ready. Starting data load...\n")

if __name__ == "__main__":
    # Load .env file from current directory
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        load_env_file(env_path)
    else:
        print(f"Warning: .env file not found at {env_path}", file=sys.stderr)
    
    # Get DATABASE_URL from environment
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("Error: DATABASE_URL not found in .env file or environment", file=sys.stderr)
        print(f"Please create .env file with: DATABASE_URL=postgresql://user:pass@host:port/dbname", file=sys.stderr)
        sys.exit(1)
    
    # Ensure psql-compatible URL (remove +psycopg2 if present)
    if database_url.startswith("postgresql+psycopg2://"):
        database_url = database_url.replace("postgresql+psycopg2://", "postgresql://", 1)
    
    jsonl_path = sys.argv[1] if len(sys.argv) > 1 else "../scaled_features.jsonl"
    jsonl_path = Path(jsonl_path).resolve()
    
    if not jsonl_path.exists():
        print(f"Error: JSONL file not found: {jsonl_path}", file=sys.stderr)
        sys.exit(1)
    
    # Ensure table exists and is empty
    ensure_table_exists(database_url)
    
    # Load the data
    load_to_production(jsonl_path, database_url)
    
    # Verify
    print("\nStep 3: Verifying load...")
    verify_sql = "SELECT COUNT(*) as total_rows, MIN(date) as earliest_date, MAX(date) as latest_date, COUNT(DISTINCT site_id) as unique_sites FROM scaled_features;"
    
    # Try psql first
    try:
        result = subprocess.run(["psql", "--version"], capture_output=True, text=True)
        psql_available = (result.returncode == 0)
    except FileNotFoundError:
        psql_available = False
    
    if psql_available:
        verify_cmd = ["psql", database_url, "-c", verify_sql]
        result = subprocess.run(verify_cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print(result.stdout)
        else:
            print(f"Warning: Could not verify load: {result.stderr}")
    elif PSYCOPG2_AVAILABLE:
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        cur.execute(verify_sql)
        row = cur.fetchone()
        print(f"Total rows: {row[0]}, Date range: {row[1]} to {row[2]}, Unique sites: {row[3]}")
        cur.close()
        conn.close()
    else:
        print("Could not verify load (no database client available)")

