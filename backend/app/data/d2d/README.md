# Date-to-Date Scaled Features Loader

This directory contains scripts to load `scaled_features.jsonl` into the database.

## Files

- `jsonl_to_tsv.py` - Converts JSONL format to TSV for PostgreSQL COPY import
- `load_dev.ps1` - PowerShell script to load into development database (Docker)
- `load_prod.ps1` - PowerShell script to load into production database (Render)

## Usage

### Development (Docker Compose)

The dev script uses the database from `docker-compose.dev.yml`:

```powershell
cd backend/app/data/d2d
.\load_dev.ps1
```

Or specify a custom JSONL path:

```powershell
.\load_dev.ps1 ..\scaled_features.jsonl
```

### Production (Render)

Get your `DATABASE_URL` from the Render dashboard and run:

```powershell
cd backend/app/data/d2d
.\load_prod.ps1 $env:DATABASE_URL
```

Or pass it directly:

```powershell
.\load_prod.ps1 "postgresql://user:pass@host:port/dbname" ..\scaled_features.jsonl
```

## Requirements

- Python 3.x (for `jsonl_to_tsv.py`)
- PostgreSQL client (`psql`) in PATH
- For dev: Docker Compose with postgres service running

## What the Scripts Do

1. **Create table** (if not exists): Creates `scaled_features` table with composite primary key
2. **Truncate**: Clears existing data (for yearly refresh)
3. **Convert & Load**: Streams JSONL → TSV → PostgreSQL COPY (efficient for large files)
4. **Verify**: Shows row count and date range

## Table Schema

```sql
CREATE TABLE scaled_features (
    site_id integer NOT NULL,
    date date NOT NULL,
    features double precision[] NOT NULL,
    PRIMARY KEY (site_id, date)
);
```

The `features` column is a PostgreSQL array of floating-point numbers, storing the scaled feature vector for each site-date combination.

