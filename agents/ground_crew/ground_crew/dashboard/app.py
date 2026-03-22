"""Ground Crew – Monitoring Dashboard.

Launch with:  streamlit run ground_crew/dashboard/app.py
"""

from __future__ import annotations

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from ground_crew.db import get_engine
from ground_crew.dashboard import queries

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Ground Crew Dashboard",
    page_icon="🪂",
    layout="wide",
    initial_sidebar_state="expanded",
)

ACCENT = "#6366f1"
SUCCESS = "#22c55e"
WARNING = "#f59e0b"
DANGER = "#ef4444"
MUTED = "#94a3b8"

STATUS_COLORS = {
    "ok": SUCCESS,
    "redirected": WARNING,
    "blocked": DANGER,
    "error": DANGER,
    "timeout": "#f97316",
    "dead": "#7f1d1d",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@st.cache_resource
def _engine():
    return get_engine()


@st.cache_data(ttl=120)
def _query(fn_name: str, **kwargs):
    fn = getattr(queries, fn_name)
    return fn(_engine(), **kwargs)


def metric_card(label: str, value, delta=None, help_text=None):
    st.metric(label=label, value=value, delta=delta, help=help_text)


def pct(part, total):
    if total == 0:
        return "0%"
    return f"{part / total * 100:.1f}%"


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.title("🪂 Ground Crew")
    st.caption("Paragliding site monitoring dashboard")
    st.divider()

    page = st.radio(
        "Navigation",
        [
            "Overview",
            "Pipeline Status",
            "Site Coverage",
            "Validation Health",
            "Feature Extraction",
            "Cost & Usage",
            "Candidates Explorer",
        ],
        label_visibility="collapsed",
    )

    st.divider()
    if st.button("🔄 Refresh data", width="stretch"):
        st.cache_data.clear()
        st.rerun()

    st.caption("Data refreshes every 2 min automatically.")


# ═══════════════════════════════════════════════════════════════════════════
# PAGE: Overview
# ═══════════════════════════════════════════════════════════════════════════

if page == "Overview":
    st.header("System Overview")

    # -- KPI row ---------------------------------------------------------
    row_counts = _query("table_row_counts")
    rc = dict(zip(row_counts["table"], row_counts["rows"]))

    k1, k2, k3, k4, k5, k6 = st.columns(6)
    with k1:
        metric_card("Extraction Runs", f"{rc.get('extraction_runs', 0):,}")
    with k2:
        metric_card("Candidates", f"{rc.get('extraction_candidates', 0):,}")
    with k3:
        metric_card("Validations", f"{rc.get('candidate_validations', 0):,}")
    with k4:
        metric_card("Validation Runs", f"{rc.get('candidate_validation_runs', 0):,}")
    with k5:
        metric_card("Webcam Extr.", f"{rc.get('webcam_extractions', 0):,}")
    with k6:
        metric_card("Meteostation Extr.", f"{rc.get('meteostation_extractions', 0):,}")

    st.divider()

    # -- Platform data freshness ----------------------------------------
    col_fresh, col_sites = st.columns([3, 2])

    with col_fresh:
        st.subheader("Platform Data Freshness")
        freshness = _query("platform_data_freshness")
        st.dataframe(
            freshness,
            width="stretch",
            hide_index=True,
            column_config={
                "source": st.column_config.TextColumn("Data Source"),
                "latest_record": st.column_config.TextColumn("Latest Record"),
                "total_rows": st.column_config.NumberColumn("Total Rows", format="%d"),
            },
        )

    with col_sites:
        st.subheader("Sites by Country")
        sites = _query("sites_summary")
        fig = px.bar(
            sites,
            x="country",
            y="site_count",
            color_discrete_sequence=[ACCENT],
            text_auto=True,
        )
        fig.update_layout(
            xaxis_title=None,
            yaxis_title="Sites",
            margin=dict(t=10, b=10),
            height=300,
        )
        st.plotly_chart(fig, width="stretch")

    st.divider()

    # -- Agents summary --------------------------------------------------
    st.subheader("Agent Performance Summary")
    agents = _query("extraction_runs_by_agent")
    st.dataframe(
        agents,
        width="stretch",
        hide_index=True,
        column_config={
            "agent": "Agent",
            "model": "Model",
            "run_count": st.column_config.NumberColumn("Runs"),
            "total_candidates": st.column_config.NumberColumn("Candidates"),
            "avg_duration_s": st.column_config.NumberColumn("Avg Duration (s)", format="%.1f"),
            "total_cost": st.column_config.NumberColumn("Total Cost ($)", format="$%.2f"),
            "avg_cost_per_run": st.column_config.NumberColumn("Avg $/Run", format="$%.4f"),
            "first_run": st.column_config.DatetimeColumn("First Run", format="YYYY-MM-DD"),
            "last_run": st.column_config.DatetimeColumn("Last Run", format="YYYY-MM-DD"),
        },
    )

    # -- Cost summary ----------------------------------------------------
    st.subheader("Cost by Pipeline Stage")
    costs = _query("cost_summary")
    st.dataframe(
        costs,
        width="stretch",
        hide_index=True,
        column_config={
            "pipeline_stage": "Stage",
            "runs": st.column_config.NumberColumn("Runs"),
            "total_cost": st.column_config.NumberColumn("Total ($)", format="$%.2f"),
            "avg_cost": st.column_config.NumberColumn("Avg ($)", format="$%.4f"),
            "total_tokens": st.column_config.NumberColumn("Tokens", format="%d"),
        },
    )


# ═══════════════════════════════════════════════════════════════════════════
# PAGE: Pipeline Status
# ═══════════════════════════════════════════════════════════════════════════

elif page == "Pipeline Status":
    st.header("Pipeline Status")

    # -- Daily activity -------------------------------------------------
    daily = _query("daily_extraction_activity")

    if not daily.empty:
        col_runs, col_cost = st.columns(2)

        with col_runs:
            st.subheader("Daily Extraction Runs & Candidates")
            fig = go.Figure()
            fig.add_trace(go.Bar(x=daily["day"], y=daily["runs"], name="Runs", marker_color=ACCENT))
            fig.add_trace(go.Bar(x=daily["day"], y=daily["candidates"], name="Candidates", marker_color="#a5b4fc"))
            fig.update_layout(
                barmode="group",
                margin=dict(t=10, b=10),
                height=350,
                legend=dict(orientation="h", y=1.05),
            )
            st.plotly_chart(fig, width="stretch")

        with col_cost:
            st.subheader("Daily Cost ($)")
            daily_c = _query("daily_costs")
            if not daily_c.empty:
                fig2 = px.area(daily_c, x="day", y="cost", color_discrete_sequence=[ACCENT])
                fig2.update_layout(margin=dict(t=10, b=10), height=350, yaxis_title="Cost ($)")
                st.plotly_chart(fig2, width="stretch")
    else:
        st.info("No extraction activity recorded yet.")

    st.divider()

    # -- Validation status pie -------------------------------------------
    st.subheader("Validation Status Distribution")
    val_status = _query("validation_status_breakdown")

    if not val_status.empty:
        col_pie, col_table = st.columns([1, 2])
        with col_pie:
            colors = [STATUS_COLORS.get(s, MUTED) for s in val_status["status"]]
            fig3 = px.pie(
                val_status,
                values="count",
                names="status",
                color="status",
                color_discrete_map=STATUS_COLORS,
                hole=0.45,
            )
            fig3.update_layout(margin=dict(t=10, b=10), height=350)
            st.plotly_chart(fig3, width="stretch")

        with col_table:
            st.dataframe(
                val_status,
                width="stretch",
                hide_index=True,
                column_config={
                    "status": "Status",
                    "count": st.column_config.NumberColumn("Count"),
                    "avg_latency_ms": st.column_config.NumberColumn("Avg Latency (ms)"),
                    "median_latency_ms": st.column_config.NumberColumn("Median (ms)"),
                    "p95_latency_ms": st.column_config.NumberColumn("P95 (ms)"),
                },
            )

    # -- Evidence flags --------------------------------------------------
    st.subheader("Candidate Evidence Coverage")
    evidence = _query("evidence_flag_counts")
    if not evidence.empty:
        row = evidence.iloc[0]
        total = int(row["total"])
        flags = ["takeoff_landing", "rules", "fees", "access", "meteostation", "webcams"]
        labels = ["Takeoff / Landing", "Rules", "Fees", "Access", "Meteostation", "Webcams"]
        vals = [int(row[f]) for f in flags]

        fig_ev = go.Figure(go.Bar(
            x=vals,
            y=labels,
            orientation="h",
            marker_color=ACCENT,
            text=[f"{v} ({pct(v, total)})" for v in vals],
            textposition="auto",
        ))
        fig_ev.update_layout(
            xaxis_title="Candidates",
            margin=dict(t=10, b=10, l=10),
            height=280,
        )
        st.plotly_chart(fig_ev, width="stretch")


# ═══════════════════════════════════════════════════════════════════════════
# PAGE: Site Coverage
# ═══════════════════════════════════════════════════════════════════════════

elif page == "Site Coverage":
    st.header("Site Coverage")

    coverage = _query("site_coverage")

    if not coverage.empty:
        total_sites = len(coverage)
        covered = len(coverage[coverage["extraction_runs"] > 0])
        with_webcam = len(coverage[coverage["webcam_extracted"] > 0])
        with_meteo = len(coverage[coverage["meteostation_extracted"] > 0])

        k1, k2, k3, k4 = st.columns(4)
        with k1:
            metric_card("Total Sites", total_sites)
        with k2:
            metric_card("Sites with Extractions", f"{covered}", delta=pct(covered, total_sites))
        with k3:
            metric_card("Sites with Webcam", f"{with_webcam}", delta=pct(with_webcam, total_sites))
        with k4:
            metric_card("Sites with Meteostation", f"{with_meteo}", delta=pct(with_meteo, total_sites))

        st.divider()

        # -- Heatmap by country -------------------------------------------
        st.subheader("Coverage by Country")
        country_cov = (
            coverage.groupby("country")
            .agg(
                sites=("site_id", "count"),
                with_runs=("extraction_runs", lambda s: (s > 0).sum()),
                with_webcam=("webcam_extracted", lambda s: (s > 0).sum()),
                with_meteo=("meteostation_extracted", lambda s: (s > 0).sum()),
            )
            .reset_index()
        )
        country_cov["extraction_pct"] = (country_cov["with_runs"] / country_cov["sites"] * 100).round(1)
        country_cov["webcam_pct"] = (country_cov["with_webcam"] / country_cov["sites"] * 100).round(1)
        country_cov["meteo_pct"] = (country_cov["with_meteo"] / country_cov["sites"] * 100).round(1)

        st.dataframe(
            country_cov.sort_values("sites", ascending=False),
            width="stretch",
            hide_index=True,
            column_config={
                "country": "Country",
                "sites": st.column_config.NumberColumn("Sites"),
                "with_runs": st.column_config.NumberColumn("Extracted"),
                "with_webcam": st.column_config.NumberColumn("Webcam"),
                "with_meteo": st.column_config.NumberColumn("Meteo"),
                "extraction_pct": st.column_config.ProgressColumn(
                    "Extraction %", min_value=0, max_value=100, format="%.1f%%"
                ),
                "webcam_pct": st.column_config.ProgressColumn(
                    "Webcam %", min_value=0, max_value=100, format="%.1f%%"
                ),
                "meteo_pct": st.column_config.ProgressColumn(
                    "Meteo %", min_value=0, max_value=100, format="%.1f%%"
                ),
            },
        )

        st.divider()

        # -- Full site table -----------------------------------------------
        st.subheader("All Sites")

        filter_country = st.multiselect("Filter by country", options=sorted(coverage["country"].dropna().unique()))
        show_coverage = coverage.copy()
        if filter_country:
            show_coverage = show_coverage[show_coverage["country"].isin(filter_country)]

        show_only = st.radio(
            "Show",
            ["All", "Missing extraction", "Missing webcam", "Missing meteostation"],
            horizontal=True,
        )
        if show_only == "Missing extraction":
            show_coverage = show_coverage[show_coverage["extraction_runs"] == 0]
        elif show_only == "Missing webcam":
            show_coverage = show_coverage[show_coverage["webcam_extracted"] == 0]
        elif show_only == "Missing meteostation":
            show_coverage = show_coverage[show_coverage["meteostation_extracted"] == 0]

        st.dataframe(
            show_coverage,
            width="stretch",
            hide_index=True,
            height=500,
            column_config={
                "site_id": st.column_config.NumberColumn("ID", width="small"),
                "name": "Site Name",
                "country": "Country",
                "extraction_runs": st.column_config.NumberColumn("Runs"),
                "candidates": st.column_config.NumberColumn("Cand."),
                "validated_ok": st.column_config.NumberColumn("Valid OK"),
                "validated_other": st.column_config.NumberColumn("Other"),
                "webcam_extracted": st.column_config.NumberColumn("Webcam"),
                "meteostation_extracted": st.column_config.NumberColumn("Meteo"),
            },
        )
    else:
        st.info("No site data available.")


# ═══════════════════════════════════════════════════════════════════════════
# PAGE: Validation Health
# ═══════════════════════════════════════════════════════════════════════════

elif page == "Validation Health":
    st.header("Validation Health")

    # -- Summary ---------------------------------------------------------
    val_status = _query("validation_status_breakdown")
    if not val_status.empty:
        total = int(val_status["count"].sum())
        ok_count = int(val_status.loc[val_status["status"] == "ok", "count"].sum())

        k1, k2, k3 = st.columns(3)
        with k1:
            metric_card("Total Validated", f"{total:,}")
        with k2:
            metric_card("Healthy (OK)", f"{ok_count:,}", delta=pct(ok_count, total))
        with k3:
            metric_card("Issues", f"{total - ok_count:,}")

        st.divider()

        col_chart, col_latency = st.columns(2)

        with col_chart:
            st.subheader("Status Breakdown")
            fig = px.bar(
                val_status,
                x="status",
                y="count",
                color="status",
                color_discrete_map=STATUS_COLORS,
                text_auto=True,
            )
            fig.update_layout(
                showlegend=False,
                margin=dict(t=10, b=10),
                height=350,
                xaxis_title=None,
                yaxis_title="Candidates",
            )
            st.plotly_chart(fig, width="stretch")

        with col_latency:
            st.subheader("Latency by Status")
            fig2 = go.Figure()
            fig2.add_trace(go.Bar(
                x=val_status["status"], y=val_status["avg_latency_ms"],
                name="Avg", marker_color=ACCENT,
            ))
            fig2.add_trace(go.Bar(
                x=val_status["status"], y=val_status["median_latency_ms"],
                name="Median", marker_color="#a5b4fc",
            ))
            fig2.add_trace(go.Bar(
                x=val_status["status"], y=val_status["p95_latency_ms"],
                name="P95", marker_color="#f59e0b",
            ))
            fig2.update_layout(
                barmode="group",
                margin=dict(t=10, b=10),
                height=350,
                yaxis_title="Latency (ms)",
                legend=dict(orientation="h", y=1.05),
            )
            st.plotly_chart(fig2, width="stretch")

    st.divider()

    # -- Validation runs ------------------------------------------------
    st.subheader("Validation Runs")
    val_runs = _query("validation_runs")
    if not val_runs.empty:
        st.dataframe(val_runs, width="stretch", hide_index=True)
    else:
        st.caption("No validation runs recorded.")

    st.divider()

    # -- Problem candidates ---------------------------------------------
    st.subheader("Problem Candidates (non-OK)")
    errors = _query("validation_errors")
    if not errors.empty:
        status_filter = st.multiselect(
            "Filter by status",
            options=sorted(errors["status"].unique()),
            default=sorted(errors["status"].unique()),
        )
        filtered = errors[errors["status"].isin(status_filter)] if status_filter else errors
        st.dataframe(
            filtered,
            width="stretch",
            hide_index=True,
            height=400,
            column_config={
                "candidate_id": st.column_config.NumberColumn("ID", width="small"),
                "name": "Name",
                "url": st.column_config.LinkColumn("URL"),
                "host": "Host",
                "site_id": st.column_config.NumberColumn("Site"),
                "status": "Status",
                "http_status": st.column_config.NumberColumn("HTTP"),
                "error": "Error",
                "latency_ms": st.column_config.NumberColumn("Latency (ms)"),
                "validated_at": st.column_config.DatetimeColumn("Validated At"),
            },
        )
    else:
        st.success("All candidates validated OK!")


# ═══════════════════════════════════════════════════════════════════════════
# PAGE: Feature Extraction
# ═══════════════════════════════════════════════════════════════════════════

elif page == "Feature Extraction":
    st.header("Feature Extraction")

    tab_webcam, tab_meteo, tab_progress = st.tabs(["Webcams", "Meteostations", "Progress"])

    # -- Webcams ---------------------------------------------------------
    with tab_webcam:
        webcams = _query("webcam_extractions")
        if not webcams.empty:
            found = int(webcams["found"].sum())
            total = len(webcams)

            c1, c2, c3, c4 = st.columns(4)
            with c1:
                metric_card("Total Extractions", total)
            with c2:
                metric_card("Found", found, delta=pct(found, total))
            with c3:
                metric_card("Not Found", total - found)
            with c4:
                avg_cost = webcams["usage_total_cost"].mean()
                metric_card("Avg Cost", f"${avg_cost:.4f}" if pd.notna(avg_cost) else "N/A")

            st.dataframe(
                webcams,
                width="stretch",
                hide_index=True,
                column_config={
                    "extraction_id": st.column_config.NumberColumn("ID", width="small"),
                    "candidate_id": st.column_config.NumberColumn("Cand. ID", width="small"),
                    "candidate_name": "Candidate",
                    "candidate_url": st.column_config.LinkColumn("Source URL"),
                    "site_id": st.column_config.NumberColumn("Site"),
                    "site_name": "Site",
                    "found": st.column_config.CheckboxColumn("Found"),
                    "webcam_url": st.column_config.LinkColumn("Webcam URL"),
                    "agent": "Agent",
                    "model": "Model",
                    "duration_seconds": st.column_config.NumberColumn("Duration (s)", format="%.1f"),
                    "usage_total_tokens": st.column_config.NumberColumn("Tokens"),
                    "usage_total_cost": st.column_config.NumberColumn("Cost ($)", format="$%.4f"),
                    "extracted_at": st.column_config.DatetimeColumn("Extracted"),
                },
            )
        else:
            st.info("No webcam extractions yet.")

    # -- Meteostations ---------------------------------------------------
    with tab_meteo:
        meteo = _query("meteostation_extractions")
        if not meteo.empty:
            found = int(meteo["found"].sum())
            total = len(meteo)

            c1, c2, c3, c4 = st.columns(4)
            with c1:
                metric_card("Total Extractions", total)
            with c2:
                metric_card("Found", found, delta=pct(found, total))
            with c3:
                metric_card("Not Found", total - found)
            with c4:
                avg_cost = meteo["usage_total_cost"].mean()
                metric_card("Avg Cost", f"${avg_cost:.4f}" if pd.notna(avg_cost) else "N/A")

            st.dataframe(
                meteo,
                width="stretch",
                hide_index=True,
                column_config={
                    "extraction_id": st.column_config.NumberColumn("ID", width="small"),
                    "candidate_id": st.column_config.NumberColumn("Cand. ID", width="small"),
                    "candidate_name": "Candidate",
                    "candidate_url": st.column_config.LinkColumn("Source URL"),
                    "site_id": st.column_config.NumberColumn("Site"),
                    "site_name": "Site",
                    "found": st.column_config.CheckboxColumn("Found"),
                    "meteostation_url": st.column_config.LinkColumn("Meteostation URL"),
                    "agent": "Agent",
                    "model": "Model",
                    "duration_seconds": st.column_config.NumberColumn("Duration (s)", format="%.1f"),
                    "usage_total_tokens": st.column_config.NumberColumn("Tokens"),
                    "usage_total_cost": st.column_config.NumberColumn("Cost ($)", format="$%.4f"),
                    "extracted_at": st.column_config.DatetimeColumn("Extracted"),
                },
            )
        else:
            st.info("No meteostation extractions yet.")

    # -- Progress --------------------------------------------------------
    with tab_progress:
        progress = _query("feature_extraction_progress")
        if not progress.empty:
            st.subheader("Per-Site Extraction Progress")
            st.dataframe(
                progress,
                width="stretch",
                hide_index=True,
                height=600,
                column_config={
                    "site_id": st.column_config.NumberColumn("ID", width="small"),
                    "site_name": "Site",
                    "country": "Country",
                    "total_candidates": st.column_config.NumberColumn("Candidates"),
                    "validated_ok": st.column_config.NumberColumn("Valid OK"),
                    "webcam_flagged": st.column_config.NumberColumn("Webcam Flagged"),
                    "meteostation_flagged": st.column_config.NumberColumn("Meteo Flagged"),
                    "webcam_extracted": st.column_config.NumberColumn("Webcam Done"),
                    "meteostation_extracted": st.column_config.NumberColumn("Meteo Done"),
                },
            )


# ═══════════════════════════════════════════════════════════════════════════
# PAGE: Cost & Usage
# ═══════════════════════════════════════════════════════════════════════════

elif page == "Cost & Usage":
    st.header("Cost & Usage")

    costs = _query("cost_summary")

    if not costs.empty:
        total_cost = costs["total_cost"].sum()
        total_tokens = costs["total_tokens"].sum()
        total_runs = costs["runs"].sum()

        k1, k2, k3 = st.columns(3)
        with k1:
            metric_card("Total Spend", f"${total_cost:.2f}")
        with k2:
            metric_card("Total Tokens", f"{int(total_tokens):,}")
        with k3:
            metric_card("Total Agent Runs", f"{int(total_runs):,}")

        st.divider()

        col_stage, col_daily = st.columns(2)

        with col_stage:
            st.subheader("Cost by Stage")
            fig = px.bar(
                costs,
                x="pipeline_stage",
                y="total_cost",
                color_discrete_sequence=[ACCENT],
                text_auto="$.2f",
            )
            fig.update_layout(
                margin=dict(t=10, b=10),
                height=350,
                xaxis_title=None,
                yaxis_title="Total Cost ($)",
            )
            st.plotly_chart(fig, width="stretch")

        with col_daily:
            st.subheader("Daily Spend")
            daily_c = _query("daily_costs")
            if not daily_c.empty:
                fig2 = go.Figure()
                fig2.add_trace(go.Scatter(
                    x=daily_c["day"],
                    y=daily_c["cost"],
                    mode="lines+markers",
                    fill="tozeroy",
                    marker_color=ACCENT,
                    line_color=ACCENT,
                ))
                fig2.update_layout(
                    margin=dict(t=10, b=10),
                    height=350,
                    yaxis_title="Cost ($)",
                )
                st.plotly_chart(fig2, width="stretch")

        st.divider()

        # -- Detailed cost table ------------------------------------------
        st.subheader("Stage Details")
        st.dataframe(
            costs,
            width="stretch",
            hide_index=True,
            column_config={
                "pipeline_stage": "Stage",
                "runs": st.column_config.NumberColumn("Runs"),
                "total_cost": st.column_config.NumberColumn("Total ($)", format="$%.2f"),
                "avg_cost": st.column_config.NumberColumn("Avg ($)", format="$%.4f"),
                "total_tokens": st.column_config.NumberColumn("Total Tokens", format="%d"),
            },
        )

        # -- Per-run cost distribution ------------------------------------
        st.subheader("Per-Run Cost Distribution (Candidate Retrieval)")
        runs = _query("extraction_runs_overview")
        if not runs.empty and "usage_total_cost" in runs.columns:
            run_costs = runs["usage_total_cost"].dropna()
            if not run_costs.empty:
                fig3 = px.histogram(
                    run_costs,
                    nbins=30,
                    color_discrete_sequence=[ACCENT],
                    labels={"value": "Cost ($)"},
                )
                fig3.update_layout(
                    margin=dict(t=10, b=10),
                    height=300,
                    xaxis_title="Cost ($)",
                    yaxis_title="Count",
                    showlegend=False,
                )
                st.plotly_chart(fig3, width="stretch")
    else:
        st.info("No cost data available yet.")


# ═══════════════════════════════════════════════════════════════════════════
# PAGE: Candidates Explorer
# ═══════════════════════════════════════════════════════════════════════════

elif page == "Candidates Explorer":
    st.header("Candidates Explorer")

    candidates = _query("candidates_overview")

    if not candidates.empty:
        # Filters
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            countries = sorted(candidates["country"].dropna().unique())
            sel_country = st.multiselect("Country", countries)
        with col_f2:
            statuses = sorted(candidates["validation_status"].dropna().unique())
            sel_status = st.multiselect("Validation Status", statuses)
        with col_f3:
            sel_host = st.text_input("Host contains")

        filtered = candidates.copy()
        if sel_country:
            filtered = filtered[filtered["country"].isin(sel_country)]
        if sel_status:
            filtered = filtered[filtered["validation_status"].isin(sel_status)]
        if sel_host:
            filtered = filtered[filtered["host"].str.contains(sel_host, case=False, na=False)]

        st.caption(f"Showing {len(filtered):,} of {len(candidates):,} candidates")

        st.dataframe(
            filtered,
            width="stretch",
            hide_index=True,
            height=600,
            column_config={
                "candidate_id": st.column_config.NumberColumn("ID", width="small"),
                "run_id": st.column_config.NumberColumn("Run", width="small"),
                "site_id": st.column_config.NumberColumn("Site ID", width="small"),
                "site_name": "Site",
                "country": "Country",
                "name": "Candidate Name",
                "url": st.column_config.LinkColumn("URL"),
                "host": "Host",
                "takeoff_landing_areas": st.column_config.CheckboxColumn("T/L"),
                "rules": st.column_config.CheckboxColumn("Rules"),
                "fees": st.column_config.CheckboxColumn("Fees"),
                "access": st.column_config.CheckboxColumn("Access"),
                "meteostation": st.column_config.CheckboxColumn("Meteo"),
                "webcams": st.column_config.CheckboxColumn("Webcam"),
                "validation_status": "Status",
            },
        )

        st.divider()

        # Top hosts
        st.subheader("Most Frequent Hosts")
        top = _query("top_hosts", limit=25)
        if not top.empty:
            fig = px.bar(
                top,
                y="host",
                x="candidate_count",
                orientation="h",
                color_discrete_sequence=[ACCENT],
                text_auto=True,
            )
            fig.update_layout(
                margin=dict(t=10, b=10),
                height=max(300, len(top) * 28),
                xaxis_title="Candidates",
                yaxis_title=None,
                yaxis=dict(autorange="reversed"),
            )
            st.plotly_chart(fig, width="stretch")
    else:
        st.info("No candidates available yet.")
