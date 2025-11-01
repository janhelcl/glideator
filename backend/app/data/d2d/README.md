# Date-to-Date Scaled Features Loader

This directory contains scripts to load `scaled_features.jsonl` into the database.

## Files

- `jsonl_to_tsv.py` - Converts JSONL format to TSV for PostgreSQL COPY import
- `load_to_docker.py` - Python script to load into development database (Docker) - **recommended for dev**
- `load_to_prod.py` - Python script to load into production database (Render) - **recommended for prod**
- `load_dev.ps1` - PowerShell script to load into development database (requires `psql` in PATH)
- `load_prod.ps1` - PowerShell script to load into production database (requires `psql` in PATH)

## Usage

### Development (Docker Compose) - Recommended Method

The easiest way to load into the dev database is using the Python helper script that handles encoding properly:

```powershell
cd backend/app/data/d2d
py load_to_docker.py ..\scaled_features.jsonl
```

This script:
- Automatically detects the Docker postgres container (`backend-postgres-1`)
- Handles UTF-8 encoding correctly
- Streams data directly (no intermediate files)
- Shows progress every 10,000 rows
- Verifies completion

**Example output:**
```
Starting conversion and load from C:\Users\...\scaled_features.jsonl...
This may take several minutes...
Processed 10000 rows...
Processed 20000 rows...
...
Successfully loaded 354144 rows!
COPY 354144
```

### Alternative: Using PowerShell Scripts

If you have `psql` in your PATH, you can use:

```powershell
cd backend/app/data/d2d
.\load_dev.ps1
```

Or specify a custom JSONL path:

```powershell
.\load_dev.ps1 ..\scaled_features.jsonl
```

### Production (Render) - Recommended Method

**Step 1: Create `.env` file**

Create a `.env` file in the `d2d` directory with your Render database URL:

```powershell
cd backend/app/data/d2d
echo "DATABASE_URL=postgresql://user:pass@host:port/dbname" > .env
```

You can get the `DATABASE_URL` from the Render dashboard under your Postgres database settings.

**Step 2: Install psycopg2 (if not already installed)**

```powershell
py -m pip install --user psycopg2-binary
```

**Step 3: Run the load script**

```powershell
cd backend/app/data/d2d
py load_to_prod.py ..\scaled_features.jsonl
```

This script:
- Automatically reads `DATABASE_URL` from `.env` file
- Uses `psycopg2` (no need for `psql` command)
- Handles UTF-8 encoding correctly
- Shows progress every 50,000 rows
- Verifies completion automatically

**Example output:**
```
Step 1: Ensuring table exists...
Step 2: Truncating existing data...
Table ready. Starting data load...

Starting conversion and load from C:\Users\...\scaled_features.jsonl...
Connecting to production database via psycopg2...
This may take several minutes...
Processed 50000 rows...
Processed 100000 rows...
...
Successfully loaded 354144 rows!

Step 3: Verifying load...
Total rows: 354144, Date range: 2021-01-01 to 2024-11-30, Unique sites: 248
```

### Alternative: Using PowerShell Script (requires psql)

If you have `psql` in your PATH, you can use:

```powershell
cd backend/app/data/d2d
.\load_prod.ps1 $env:DATABASE_URL
```

Or pass it directly:

```powershell
.\load_prod.ps1 "postgresql://user:pass@host:port/dbname" ..\scaled_features.jsonl
```

## Requirements

- Python 3.x (for conversion scripts)
- For dev: Docker Compose with postgres service running (`backend-postgres-1`)
- For prod: 
  - `psycopg2-binary` Python package (install with `pip install psycopg2-binary`)
  - `.env` file with `DATABASE_URL` in the `d2d` directory
  - OR: PostgreSQL client (`psql`) in PATH if using PowerShell script

## What the Scripts Do

1. **Create table** (if not exists): Creates `scaled_features` table with composite primary key
2. **Truncate**: Clears existing data (for yearly refresh)
3. **Convert & Load**: Streams JSONL → TSV → PostgreSQL COPY (efficient for large files ~1.6GB)
4. **Verify**: Shows row count and date range

## Table Schema

```sql
CREATE TABLE scaled_features (
    site_id integer NOT NULL,
    date date NOT NULL,
    features double precision[] NOT NULL,
    PRIMARY KEY (site_id, date)
);

CREATE INDEX idx_scaled_features_date ON scaled_features(date);
```

The `features` column is a PostgreSQL array of floating-point numbers, storing the scaled feature vector for each site-date combination.

## Verification

After loading, verify the data:

```sql
SELECT 
    COUNT(*) as total_rows, 
    MIN(date) as earliest_date, 
    MAX(date) as latest_date,
    COUNT(DISTINCT site_id) as unique_sites 
FROM scaled_features;
```

**Expected result (as of 2024-11-30):**
- ~354,144 rows
- Date range: 2021-01-01 to 2024-11-30
- ~248 unique sites

## Loading Process Details

### Development Loading

The data was successfully loaded into dev using the `load_to_docker.py` script:

1. **File Location**: `backend/app/data/scaled_features.jsonl` (1.6GB)
2. **Conversion**: The script streams JSONL → TSV format on-the-fly
3. **Loading**: Data is piped directly into Docker postgres container via `docker exec`
4. **Result**: 354,144 rows loaded successfully

The helper script (`load_to_docker.py`) handles:
- Proper UTF-8 encoding (avoids PowerShell encoding issues)
- Streaming (no memory issues with large files)
- Progress reporting (every 10,000 rows)
- Error handling

### Production Loading

The production load uses `load_to_prod.py`:

1. **Setup**: Create `.env` file with `DATABASE_URL` from Render dashboard
2. **Dependencies**: Install `psycopg2-binary` (`pip install psycopg2-binary`)
3. **Execution**: Run `py load_to_prod.py ..\scaled_features.jsonl`
4. **Process**: 
   - Creates/verifies table structure
   - Truncates existing data
   - Converts JSONL to TSV in temp file
   - Loads via PostgreSQL COPY using psycopg2
   - Verifies the load

The script automatically detects available tools (psql or psycopg2) and uses the best available method.

**Note**: The TSV file (`scaled_features.tsv`, ~3GB) is generated automatically but excluded from git via `.gitignore`. For production, a temporary TSV file is created during loading and automatically cleaned up.

