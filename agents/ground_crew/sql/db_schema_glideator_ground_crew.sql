-- Schema: glideator_ground_crew
-- Purpose: Store extraction runs and candidate websites found by BUAgent and human operators
-- Created: 2025-11-12
--
-- Legacy DBs: if extraction_runs still has column "timestamp", rename to match loaders/API:
--   ALTER TABLE glideator_ground_crew.extraction_runs RENAME COLUMN timestamp TO extracted_at;

-- Create schema
CREATE SCHEMA IF NOT EXISTS glideator_ground_crew;

-- Table: extraction_runs
-- Purpose: Track each extraction execution (one row per site extraction)
CREATE TABLE glideator_ground_crew.extraction_runs (
    run_id BIGSERIAL PRIMARY KEY,
    site_id INTEGER NOT NULL,
    agent VARCHAR NOT NULL,  -- 'BUAgent' or 'Human'
    model VARCHAR,  -- e.g. 'gemini-2.5-flash', NULL for Human
    extracted_at TIMESTAMPTZ NOT NULL,  -- when the extraction completed (was legacy column name "timestamp" in older dumps)
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
CREATE INDEX idx_extraction_runs_extracted_at ON glideator_ground_crew.extraction_runs(extracted_at);
CREATE INDEX idx_extraction_runs_site_extracted_at ON glideator_ground_crew.extraction_runs(site_id, extracted_at);
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

-- Table: candidate_validation_runs
-- Purpose: Track batches of candidate validation operations
CREATE TABLE glideator_ground_crew.candidate_validation_runs (
    validation_run_id BIGSERIAL PRIMARY KEY,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ,
    triggered_by VARCHAR NOT NULL DEFAULT 'cli', -- cli/manual/schedule/etc
    filters JSONB DEFAULT '{}'::jsonb,
    validator VARCHAR DEFAULT 'browser',
    candidate_total INTEGER,
    success_count INTEGER,
    failure_count INTEGER,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Table: candidate_validations
-- Purpose: Append-only records of individual validation attempts per candidate
CREATE TABLE glideator_ground_crew.candidate_validations (
    validation_id BIGSERIAL PRIMARY KEY,
    candidate_id BIGINT NOT NULL REFERENCES glideator_ground_crew.extraction_candidates(candidate_id),
    validation_run_id BIGINT REFERENCES glideator_ground_crew.candidate_validation_runs(validation_run_id),
    status VARCHAR NOT NULL,
    http_status INTEGER,
    final_url TEXT,
    latency_ms INTEGER,
    error TEXT,
    validator VARCHAR DEFAULT 'browser',
    validated_by VARCHAR,
    validated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_candidate_validations_candidate_id ON glideator_ground_crew.candidate_validations(candidate_id, validated_at DESC);
CREATE INDEX idx_candidate_validations_run_id ON glideator_ground_crew.candidate_validations(validation_run_id);
CREATE INDEX idx_candidate_validations_status ON glideator_ground_crew.candidate_validations(status, validated_at DESC);

-- Table: webcam_extractions
-- Purpose: Store webcam URLs extracted from candidate websites by WebcamExtractorAgent
CREATE TABLE glideator_ground_crew.webcam_extractions (
    extraction_id BIGSERIAL PRIMARY KEY,
    candidate_id BIGINT NOT NULL REFERENCES glideator_ground_crew.extraction_candidates(candidate_id),
    found BOOLEAN NOT NULL,
    webcam_url TEXT,
    agent VARCHAR NOT NULL DEFAULT 'BUAgent',
    model VARCHAR,
    duration_seconds NUMERIC,
    usage_total_tokens INTEGER,
    usage_total_cost NUMERIC,
    extracted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_webcam_extractions_candidate_id ON glideator_ground_crew.webcam_extractions(candidate_id);
CREATE INDEX idx_webcam_extractions_found ON glideator_ground_crew.webcam_extractions(found);

-- Table: meteostation_extractions
-- Purpose: Store meteostation URLs extracted from candidate websites by MeteostationExtractorAgent
CREATE TABLE glideator_ground_crew.meteostation_extractions (
    extraction_id BIGSERIAL PRIMARY KEY,
    candidate_id BIGINT NOT NULL REFERENCES glideator_ground_crew.extraction_candidates(candidate_id),
    found BOOLEAN NOT NULL,
    meteostation_url TEXT,
    agent VARCHAR NOT NULL DEFAULT 'BUAgent',
    model VARCHAR,
    duration_seconds NUMERIC,
    usage_total_tokens INTEGER,
    usage_total_cost NUMERIC,
    extracted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_meteostation_extractions_candidate_id ON glideator_ground_crew.meteostation_extractions(candidate_id);
CREATE INDEX idx_meteostation_extractions_found ON glideator_ground_crew.meteostation_extractions(found);

-- Example queries
-- ================

-- Get latest extraction for each site
-- SELECT DISTINCT ON (site_id) * 
-- FROM glideator_ground_crew.extraction_runs 
-- ORDER BY site_id, extracted_at DESC;

-- Get all candidates from latest run for a specific site
-- SELECT c.* 
-- FROM glideator_ground_crew.extraction_candidates c
-- JOIN glideator_ground_crew.extraction_runs r ON c.run_id = r.run_id
-- WHERE r.site_id = 123
-- ORDER BY r.extracted_at DESC 
-- LIMIT 100;

-- Summary statistics
-- SELECT 
--     COUNT(*) as total_runs,
--     COUNT(DISTINCT site_id) as unique_sites,
--     MIN(extracted_at) as earliest_extraction,
--     MAX(extracted_at) as latest_extraction,
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

