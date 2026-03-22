"""SQL queries backing the Ground Crew monitoring dashboard."""

from __future__ import annotations

import pandas as pd
from sqlalchemy.engine import Engine


# ---------------------------------------------------------------------------
# System-wide overview
# ---------------------------------------------------------------------------

def table_row_counts(engine: Engine) -> pd.DataFrame:
    return pd.read_sql(
        """
        SELECT 'extraction_runs'        AS "table", COUNT(*) AS rows FROM glideator_ground_crew.extraction_runs
        UNION ALL
        SELECT 'extraction_candidates',           COUNT(*) FROM glideator_ground_crew.extraction_candidates
        UNION ALL
        SELECT 'candidate_validations',           COUNT(*) FROM glideator_ground_crew.candidate_validations
        UNION ALL
        SELECT 'candidate_validation_runs',       COUNT(*) FROM glideator_ground_crew.candidate_validation_runs
        UNION ALL
        SELECT 'webcam_extractions',              COUNT(*) FROM glideator_ground_crew.webcam_extractions
        UNION ALL
        SELECT 'meteostation_extractions',        COUNT(*) FROM glideator_ground_crew.meteostation_extractions
        ORDER BY 1
        """,
        engine,
    )


def platform_data_freshness(engine: Engine) -> pd.DataFrame:
    return pd.read_sql(
        """
        SELECT 'Flights (source)'          AS source,
               MAX(date)::text              AS latest_record,
               COUNT(*)                     AS total_rows
        FROM source.flights
        UNION ALL
        SELECT 'GFS Weather (source)',
               MAX(date)::text,
               COUNT(*)
        FROM source.gfs
        UNION ALL
        SELECT 'Predictions (feature store)',
               MAX(date)::text,
               COUNT(*)
        FROM glideator_fs.predictions
        UNION ALL
        SELECT 'Feature rows (feature store)',
               MAX(date)::text,
               COUNT(*)
        FROM glideator_fs.features_with_target
        UNION ALL
        SELECT 'Seed sites (reference)',
               NULL,
               COUNT(*)
        FROM glideator.seed_sites
        ORDER BY 1
        """,
        engine,
    )


def sites_summary(engine: Engine) -> pd.DataFrame:
    return pd.read_sql(
        """
        SELECT country, COUNT(*) AS site_count
        FROM glideator_mart.dim_sites
        WHERE site_id <= 170
        GROUP BY country
        ORDER BY site_count DESC
        """,
        engine,
    )


# ---------------------------------------------------------------------------
# Extraction runs
# ---------------------------------------------------------------------------

def extraction_runs_overview(engine: Engine) -> pd.DataFrame:
    return pd.read_sql(
        """
        SELECT
            r.run_id,
            r.site_id,
            s.name AS site_name,
            s.country,
            r.agent,
            r.model,
            r.extracted_at,
            r.duration_seconds,
            r.candidate_count,
            r.usage_total_tokens,
            r.usage_total_cost
        FROM glideator_ground_crew.extraction_runs r
        LEFT JOIN glideator_mart.dim_sites s ON r.site_id = s.site_id
        ORDER BY r.extracted_at DESC
        """,
        engine,
    )


def extraction_runs_by_agent(engine: Engine) -> pd.DataFrame:
    return pd.read_sql(
        """
        SELECT
            agent,
            model,
            COUNT(*)                            AS run_count,
            SUM(candidate_count)                AS total_candidates,
            ROUND(AVG(duration_seconds)::numeric, 1) AS avg_duration_s,
            ROUND(SUM(usage_total_cost)::numeric, 2) AS total_cost,
            ROUND(AVG(usage_total_cost)::numeric, 4) AS avg_cost_per_run,
            MIN(extracted_at)                   AS first_run,
            MAX(extracted_at)                   AS last_run
        FROM glideator_ground_crew.extraction_runs
        GROUP BY agent, model
        ORDER BY run_count DESC
        """,
        engine,
    )


def daily_extraction_activity(engine: Engine) -> pd.DataFrame:
    return pd.read_sql(
        """
        SELECT
            DATE(extracted_at) AS day,
            COUNT(*)           AS runs,
            SUM(candidate_count) AS candidates,
            ROUND(SUM(usage_total_cost)::numeric, 2) AS cost
        FROM glideator_ground_crew.extraction_runs
        GROUP BY DATE(extracted_at)
        ORDER BY day
        """,
        engine,
    )


# ---------------------------------------------------------------------------
# Candidates
# ---------------------------------------------------------------------------

def candidates_overview(engine: Engine) -> pd.DataFrame:
    return pd.read_sql(
        """
        SELECT
            c.candidate_id,
            c.run_id,
            r.site_id,
            s.name AS site_name,
            s.country,
            c.name,
            c.url,
            c.host,
            c.takeoff_landing_areas,
            c.rules,
            c.fees,
            c.access,
            c.meteostation,
            c.webcams,
            latest_val.status AS validation_status
        FROM glideator_ground_crew.extraction_candidates c
        JOIN glideator_ground_crew.extraction_runs r ON c.run_id = r.run_id
        LEFT JOIN glideator_mart.dim_sites s ON r.site_id = s.site_id
        LEFT JOIN LATERAL (
            SELECT status
            FROM glideator_ground_crew.candidate_validations v
            WHERE v.candidate_id = c.candidate_id
            ORDER BY v.validated_at DESC
            LIMIT 1
        ) latest_val ON TRUE
        ORDER BY c.candidate_id
        """,
        engine,
    )


def evidence_flag_counts(engine: Engine) -> pd.DataFrame:
    return pd.read_sql(
        """
        SELECT
            SUM(CASE WHEN takeoff_landing_areas THEN 1 ELSE 0 END) AS takeoff_landing,
            SUM(CASE WHEN rules                 THEN 1 ELSE 0 END) AS rules,
            SUM(CASE WHEN fees                  THEN 1 ELSE 0 END) AS fees,
            SUM(CASE WHEN access                THEN 1 ELSE 0 END) AS access,
            SUM(CASE WHEN meteostation          THEN 1 ELSE 0 END) AS meteostation,
            SUM(CASE WHEN webcams               THEN 1 ELSE 0 END) AS webcams,
            COUNT(*)                                                 AS total
        FROM glideator_ground_crew.extraction_candidates
        """,
        engine,
    )


def top_hosts(engine: Engine, limit: int = 20) -> pd.DataFrame:
    return pd.read_sql(
        """
        SELECT host, COUNT(*) AS candidate_count
        FROM glideator_ground_crew.extraction_candidates
        WHERE host IS NOT NULL AND host != ''
        GROUP BY host
        ORDER BY candidate_count DESC
        LIMIT %(limit)s
        """,
        engine,
        params={"limit": limit},
    )


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validation_status_breakdown(engine: Engine) -> pd.DataFrame:
    return pd.read_sql(
        """
        WITH latest AS (
            SELECT DISTINCT ON (candidate_id)
                candidate_id, status, http_status, latency_ms, error, validated_at
            FROM glideator_ground_crew.candidate_validations
            ORDER BY candidate_id, validated_at DESC
        )
        SELECT
            status,
            COUNT(*)                                      AS count,
            ROUND(AVG(latency_ms)::numeric, 0)            AS avg_latency_ms,
            ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY latency_ms)::numeric, 0) AS median_latency_ms,
            ROUND(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY latency_ms)::numeric, 0) AS p95_latency_ms
        FROM latest
        GROUP BY status
        ORDER BY count DESC
        """,
        engine,
    )


def validation_runs(engine: Engine) -> pd.DataFrame:
    return pd.read_sql(
        """
        SELECT *
        FROM glideator_ground_crew.candidate_validation_runs
        ORDER BY validation_run_id DESC
        """,
        engine,
    )


def validation_errors(engine: Engine) -> pd.DataFrame:
    return pd.read_sql(
        """
        WITH latest AS (
            SELECT DISTINCT ON (v.candidate_id)
                v.candidate_id,
                c.name,
                c.url,
                c.host,
                r.site_id,
                v.status,
                v.http_status,
                v.error,
                v.latency_ms,
                v.validated_at
            FROM glideator_ground_crew.candidate_validations v
            JOIN glideator_ground_crew.extraction_candidates c ON v.candidate_id = c.candidate_id
            JOIN glideator_ground_crew.extraction_runs r ON c.run_id = r.run_id
            ORDER BY v.candidate_id, v.validated_at DESC
        )
        SELECT * FROM latest
        WHERE status NOT IN ('ok')
        ORDER BY status, validated_at DESC
        """,
        engine,
    )


# ---------------------------------------------------------------------------
# Feature extraction (webcam + meteostation)
# ---------------------------------------------------------------------------

def webcam_extractions(engine: Engine) -> pd.DataFrame:
    return pd.read_sql(
        """
        SELECT
            w.extraction_id,
            w.candidate_id,
            c.name AS candidate_name,
            c.url  AS candidate_url,
            r.site_id,
            s.name AS site_name,
            w.found,
            w.webcam_url,
            w.agent,
            w.model,
            w.duration_seconds,
            w.usage_total_tokens,
            w.usage_total_cost,
            w.extracted_at
        FROM glideator_ground_crew.webcam_extractions w
        JOIN glideator_ground_crew.extraction_candidates c ON w.candidate_id = c.candidate_id
        JOIN glideator_ground_crew.extraction_runs r ON c.run_id = r.run_id
        LEFT JOIN glideator_mart.dim_sites s ON r.site_id = s.site_id
        ORDER BY w.extracted_at DESC
        """,
        engine,
    )


def meteostation_extractions(engine: Engine) -> pd.DataFrame:
    return pd.read_sql(
        """
        SELECT
            m.extraction_id,
            m.candidate_id,
            c.name AS candidate_name,
            c.url  AS candidate_url,
            r.site_id,
            s.name AS site_name,
            m.found,
            m.meteostation_url,
            m.agent,
            m.model,
            m.duration_seconds,
            m.usage_total_tokens,
            m.usage_total_cost,
            m.extracted_at
        FROM glideator_ground_crew.meteostation_extractions m
        JOIN glideator_ground_crew.extraction_candidates c ON m.candidate_id = c.candidate_id
        JOIN glideator_ground_crew.extraction_runs r ON c.run_id = r.run_id
        LEFT JOIN glideator_mart.dim_sites s ON r.site_id = s.site_id
        ORDER BY m.extracted_at DESC
        """,
        engine,
    )


def feature_extraction_progress(engine: Engine) -> pd.DataFrame:
    """Per-site progress: how many candidates have webcam/meteostation flags
    vs how many have been extracted."""
    return pd.read_sql(
        """
        WITH site_candidates AS (
            SELECT
                r.site_id,
                s.name AS site_name,
                s.country,
                c.candidate_id,
                c.webcams AS has_webcam_flag,
                c.meteostation AS has_meteostation_flag,
                latest_val.status AS validation_status
            FROM glideator_ground_crew.extraction_candidates c
            JOIN glideator_ground_crew.extraction_runs r ON c.run_id = r.run_id
            LEFT JOIN glideator_mart.dim_sites s ON r.site_id = s.site_id
            LEFT JOIN LATERAL (
                SELECT status
                FROM glideator_ground_crew.candidate_validations v
                WHERE v.candidate_id = c.candidate_id
                ORDER BY v.validated_at DESC
                LIMIT 1
            ) latest_val ON TRUE
        )
        SELECT
            sc.site_id,
            sc.site_name,
            sc.country,
            COUNT(*) AS total_candidates,
            SUM(CASE WHEN sc.validation_status = 'ok' THEN 1 ELSE 0 END) AS validated_ok,
            SUM(CASE WHEN sc.has_webcam_flag THEN 1 ELSE 0 END) AS webcam_flagged,
            SUM(CASE WHEN sc.has_meteostation_flag THEN 1 ELSE 0 END) AS meteostation_flagged,
            COUNT(DISTINCT we.candidate_id) AS webcam_extracted,
            COUNT(DISTINCT me.candidate_id) AS meteostation_extracted
        FROM site_candidates sc
        LEFT JOIN glideator_ground_crew.webcam_extractions we ON sc.candidate_id = we.candidate_id
        LEFT JOIN glideator_ground_crew.meteostation_extractions me ON sc.candidate_id = me.candidate_id
        GROUP BY sc.site_id, sc.site_name, sc.country
        ORDER BY sc.site_id
        """,
        engine,
    )


# ---------------------------------------------------------------------------
# Cost tracking
# ---------------------------------------------------------------------------

def cost_summary(engine: Engine) -> pd.DataFrame:
    return pd.read_sql(
        """
        SELECT 'Candidate Retrieval' AS pipeline_stage,
               COUNT(*)             AS runs,
               ROUND(SUM(usage_total_cost)::numeric, 2)  AS total_cost,
               ROUND(AVG(usage_total_cost)::numeric, 4)  AS avg_cost,
               SUM(usage_total_tokens)                    AS total_tokens
        FROM glideator_ground_crew.extraction_runs
        UNION ALL
        SELECT 'Webcam Extraction',
               COUNT(*),
               ROUND(SUM(usage_total_cost)::numeric, 2),
               ROUND(AVG(usage_total_cost)::numeric, 4),
               SUM(usage_total_tokens)
        FROM glideator_ground_crew.webcam_extractions
        UNION ALL
        SELECT 'Meteostation Extraction',
               COUNT(*),
               ROUND(SUM(usage_total_cost)::numeric, 2),
               ROUND(AVG(usage_total_cost)::numeric, 4),
               SUM(usage_total_tokens)
        FROM glideator_ground_crew.meteostation_extractions
        """,
        engine,
    )


def daily_costs(engine: Engine) -> pd.DataFrame:
    return pd.read_sql(
        """
        SELECT day, SUM(cost) AS cost, SUM(tokens) AS tokens FROM (
            SELECT DATE(extracted_at) AS day,
                   COALESCE(usage_total_cost, 0) AS cost,
                   COALESCE(usage_total_tokens, 0) AS tokens
            FROM glideator_ground_crew.extraction_runs
            UNION ALL
            SELECT DATE(extracted_at),
                   COALESCE(usage_total_cost, 0),
                   COALESCE(usage_total_tokens, 0)
            FROM glideator_ground_crew.webcam_extractions
            UNION ALL
            SELECT DATE(extracted_at),
                   COALESCE(usage_total_cost, 0),
                   COALESCE(usage_total_tokens, 0)
            FROM glideator_ground_crew.meteostation_extractions
        ) t
        GROUP BY day
        ORDER BY day
        """,
        engine,
    )


# ---------------------------------------------------------------------------
# Site coverage
# ---------------------------------------------------------------------------

def site_coverage(engine: Engine) -> pd.DataFrame:
    """All sites and whether they have extraction runs, validated candidates, etc."""
    return pd.read_sql(
        """
        SELECT
            s.site_id,
            s.name,
            s.country,
            COALESCE(er.run_count, 0)                AS extraction_runs,
            COALESCE(er.candidate_count, 0)          AS candidates,
            COALESCE(v.validated_ok, 0)              AS validated_ok,
            COALESCE(v.validated_other, 0)           AS validated_other,
            COALESCE(f.webcam_extracted, 0)          AS webcam_extracted,
            COALESCE(f.meteostation_extracted, 0)    AS meteostation_extracted
        FROM glideator_mart.dim_sites s
        LEFT JOIN (
            SELECT site_id,
                   COUNT(DISTINCT run_id)         AS run_count,
                   COUNT(DISTINCT candidate_id)   AS candidate_count
            FROM glideator_ground_crew.extraction_runs r
            JOIN glideator_ground_crew.extraction_candidates c USING (run_id)
            GROUP BY site_id
        ) er ON s.site_id = er.site_id
        LEFT JOIN (
            SELECT r.site_id,
                   SUM(CASE WHEN lv.status = 'ok' THEN 1 ELSE 0 END) AS validated_ok,
                   SUM(CASE WHEN lv.status != 'ok' OR lv.status IS NULL THEN 1 ELSE 0 END) AS validated_other
            FROM glideator_ground_crew.extraction_candidates c
            JOIN glideator_ground_crew.extraction_runs r ON c.run_id = r.run_id
            LEFT JOIN LATERAL (
                SELECT status FROM glideator_ground_crew.candidate_validations v
                WHERE v.candidate_id = c.candidate_id
                ORDER BY v.validated_at DESC LIMIT 1
            ) lv ON TRUE
            GROUP BY r.site_id
        ) v ON s.site_id = v.site_id
        LEFT JOIN (
            SELECT r.site_id,
                   COUNT(DISTINCT we.candidate_id) AS webcam_extracted,
                   COUNT(DISTINCT me.candidate_id) AS meteostation_extracted
            FROM glideator_ground_crew.extraction_candidates c
            JOIN glideator_ground_crew.extraction_runs r ON c.run_id = r.run_id
            LEFT JOIN glideator_ground_crew.webcam_extractions we ON c.candidate_id = we.candidate_id
            LEFT JOIN glideator_ground_crew.meteostation_extractions me ON c.candidate_id = me.candidate_id
            GROUP BY r.site_id
        ) f ON s.site_id = f.site_id
        WHERE s.site_id <= 170
        ORDER BY s.site_id
        """,
        engine,
    )
