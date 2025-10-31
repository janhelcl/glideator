# PowerShell script to load scaled_features.jsonl into dev database
# Usage: .\load_dev.ps1 [path/to/scaled_features.jsonl]

param(
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

# Dev database connection (from docker-compose.dev.yml)
$DbUrl = "postgresql://postgres:postgres@localhost:5432/glideator"

Write-Host "Step 1: Ensuring table exists..." -ForegroundColor Cyan
psql $DbUrl -c "CREATE TABLE IF NOT EXISTS scaled_features (site_id integer NOT NULL, date date NOT NULL, features double precision[] NOT NULL, PRIMARY KEY (site_id, date));"
psql $DbUrl -c "CREATE INDEX IF NOT EXISTS idx_scaled_features_date ON scaled_features(date);"

if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to create table"
    exit 1
}

Write-Host "Step 2: Truncating existing data..." -ForegroundColor Cyan
psql $DbUrl -c "TRUNCATE TABLE scaled_features;"

if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to truncate table"
    exit 1
}

Write-Host "Step 3: Converting JSONL to TSV and loading into database..." -ForegroundColor Cyan
Write-Host "This may take a few minutes for large files..." -ForegroundColor Yellow

# Use Python to convert and pipe to psql COPY
python "$ScriptDir\jsonl_to_tsv.py" $JsonlPath | `
    psql $DbUrl -c "\copy scaled_features (site_id, date, features) FROM STDIN WITH (FORMAT text, DELIMITER E'\t', NULL 'NULL');"

if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to load data"
    exit 1
}

Write-Host "Step 4: Verifying load..." -ForegroundColor Cyan
psql $DbUrl -c "SELECT COUNT(*) as total_rows, MIN(date) as earliest_date, MAX(date) as latest_date FROM scaled_features;"

Write-Host "`nLoad complete!" -ForegroundColor Green

