# PowerShell script to load scaled_features.jsonl into production database (Render)
# Usage: .\load_prod.ps1 [DATABASE_URL] [path/to/scaled_features.jsonl]
#
# You can get DATABASE_URL from Render dashboard or set it as environment variable:
# $env:DATABASE_URL="postgresql://user:pass@host:port/dbname"

param(
    [Parameter(Mandatory=$true)]
    [string]$DatabaseUrl,
    
    [string]$JsonlPath = "..\scaled_features.jsonl"
)

$ErrorActionPreference = "Stop"

# Resolve paths relative to script location
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$JsonlPath = Join-Path $ScriptDir $JsonlPath

if (-not (Test-Path $JsonlPath)) {
    Write-Error "JSONL file not found: $JsonlPath"
    exit 1
}

# Ensure psql-compatible URL format (remove +psycopg2 if present)
if ($DatabaseUrl -match "^postgresql\+psycopg2://") {
    $DatabaseUrl = $DatabaseUrl -replace "^postgresql\+psycopg2://", "postgresql://"
}

Write-Host "Step 1: Ensuring table exists..." -ForegroundColor Cyan
psql $DatabaseUrl -c "CREATE TABLE IF NOT EXISTS scaled_features (site_id integer NOT NULL, date date NOT NULL, features double precision[] NOT NULL, PRIMARY KEY (site_id, date));"
psql $DatabaseUrl -c "CREATE INDEX IF NOT EXISTS idx_scaled_features_date ON scaled_features(date);"

if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to create table. Check your DATABASE_URL."
    exit 1
}

Write-Host "Step 2: Truncating existing data..." -ForegroundColor Cyan
psql $DatabaseUrl -c "TRUNCATE TABLE scaled_features;"

if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to truncate table"
    exit 1
}

Write-Host "Step 3: Converting JSONL to TSV and loading into database..." -ForegroundColor Cyan
Write-Host "This may take several minutes for large files (1.6GB)..." -ForegroundColor Yellow

# Use Python to convert and pipe to psql COPY
python "$ScriptDir\jsonl_to_tsv.py" $JsonlPath | `
    psql $DatabaseUrl -c "\copy scaled_features (site_id, date, features) FROM STDIN WITH (FORMAT text, DELIMITER E'\t', NULL 'NULL');"

if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to load data"
    exit 1
}

Write-Host "Step 4: Verifying load..." -ForegroundColor Cyan
psql $DatabaseUrl -c "SELECT COUNT(*) as total_rows, MIN(date) as earliest_date, MAX(date) as latest_date FROM scaled_features;"

Write-Host "`nLoad complete!" -ForegroundColor Green

