-- Schema: glideator_ground_crew
-- Purpose: Store extraction runs and candidate websites found by BUAgent and human operators
-- Created: 2025-11-12

-- Create schema
CREATE SCHEMA IF NOT EXISTS glideator_ground_crew;

-- Table: extraction_runs
-- Purpose: Track each extraction execution (one row per site extraction)
CREATE TABLE glideator_ground_crew.extraction_runs (
    run_id BIGSERIAL PRIMARY KEY,
    site_id INTEGER NOT NULL,
    agent VARCHAR NOT NULL,  -- 'BUAgent' or 'Human'
    model VARCHAR,  -- e.g. 'gemini-2.5-flash', NULL for Human
    timestamp TIMESTAMP NOT NULL,
    duration_seconds NUMERIC,
    usage_total_prompt_tokens INTEGER,
    usage_total_prompt_cost NUMERIC,
    usage_total_prompt_cached_tokens INTEGER,
    usage_total_prompt_cached_cost NUMERIC,
    usage_total_completion_tokens INTEGER,
    usage_total_completion_cost NUMERIC,
    usage_total_tokens INTEGER,
    usage_total_cost NUMERIC,
    usage_entry_count INTEGER,
    candidate_count INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for extraction_runs
CREATE INDEX idx_extraction_runs_site_id ON glideator_ground_crew.extraction_runs(site_id);
CREATE INDEX idx_extraction_runs_timestamp ON glideator_ground_crew.extraction_runs(timestamp);
CREATE INDEX idx_extraction_runs_site_timestamp ON glideator_ground_crew.extraction_runs(site_id, timestamp);
CREATE INDEX idx_extraction_runs_agent ON glideator_ground_crew.extraction_runs(agent);

-- Table: extraction_candidates
-- Purpose: Store candidate websites found during each extraction (one row per candidate)
CREATE TABLE glideator_ground_crew.extraction_candidates (
    candidate_id BIGSERIAL PRIMARY KEY,
    run_id BIGINT NOT NULL REFERENCES glideator_ground_crew.extraction_runs(run_id),
    name TEXT,
    url TEXT,
    host VARCHAR,  -- Domain extracted from URL
    takeoff_landing_areas BOOLEAN,
    rules BOOLEAN,
    fees BOOLEAN,
    access BOOLEAN,
    meteostation BOOLEAN,
    webcams BOOLEAN,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for extraction_candidates
CREATE INDEX idx_extraction_candidates_run_id ON glideator_ground_crew.extraction_candidates(run_id);
CREATE INDEX idx_extraction_candidates_url ON glideator_ground_crew.extraction_candidates(url);
CREATE INDEX idx_extraction_candidates_host ON glideator_ground_crew.extraction_candidates(host);

-- Example queries
-- ================

-- Get latest extraction for each site
-- SELECT DISTINCT ON (site_id) * 
-- FROM glideator_ground_crew.extraction_runs 
-- ORDER BY site_id, timestamp DESC;

-- Get all candidates from latest run for a specific site
-- SELECT c.* 
-- FROM glideator_ground_crew.extraction_candidates c
-- JOIN glideator_ground_crew.extraction_runs r ON c.run_id = r.run_id
-- WHERE r.site_id = 123
-- ORDER BY r.timestamp DESC 
-- LIMIT 100;

-- Summary statistics
-- SELECT 
--     COUNT(*) as total_runs,
--     COUNT(DISTINCT site_id) as unique_sites,
--     MIN(timestamp) as earliest_extraction,
--     MAX(timestamp) as latest_extraction,
--     SUM(candidate_count) as total_candidates_found,
--     SUM(usage_total_cost) as total_cost
-- FROM glideator_ground_crew.extraction_runs;

-- Find most common domains
-- SELECT 
--     host,
--     COUNT(*) as occurrences,
--     COUNT(DISTINCT run_id) as extraction_runs
-- FROM glideator_ground_crew.extraction_candidates
-- WHERE host IS NOT NULL
-- GROUP BY host
-- ORDER BY occurrences DESC
-- LIMIT 20;

