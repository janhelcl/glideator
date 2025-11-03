from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go


def plot_vertical_profile(row: pd.Series, hour: int = 15) -> Any:
    """
    Plot vertical profile (temperature, dewpoint, DALR, SMR) from a feats_wide row.

    Parameters
    ----------
    row : pd.Series
        A row from feats_wide DataFrame containing meteorological features
    hour : int, optional
        Which hour to plot (9, 12, or 15). Default is 15.

    Returns
    -------
    plotly.graph_objects.Figure
        The generated figure
    """
    # Define pressure levels
    PA_LVLS = [50000, 55000, 60000, 65000, 70000, 75000, 80000, 85000, 90000, 92500, 95000, 97500, 100000]
    HPA_LVLS = np.array(PA_LVLS) / 100

    # Build column names for the specified hour
    geo_iso_cols = [f"geopotential_height_{int(lvl)}hpa_m_{hour}" for lvl in HPA_LVLS]
    temp_iso_cols = [f"temperature_{int(lvl)}hpa_k_{hour}" for lvl in HPA_LVLS]
    humidity_iso_cols = [f"relative_humidity_{int(lvl)}hpa_pct_{hour}" for lvl in HPA_LVLS]
    temp_sfc_col = f"temperature_2m_k_{hour}"
    dew_point_sfc_col = f"dewpoint_2m_k_{hour}"
    geo_sfc_col = f"geopotential_height_sfc_m_{hour}"

    # Extract data from row
    geo_iso = row[geo_iso_cols].values
    temp_iso = row[temp_iso_cols].values - 273.15  # Convert K to C
    humid_iso = row[humidity_iso_cols].values
    temp_agl = row[temp_sfc_col] - 273.15
    geo_sfc = row[geo_sfc_col]
    dewpoint_sfc = row[dew_point_sfc_col] - 273.15

    # Calculate dewpoint for isobaric levels
    def dew_point(temp_c, rh_percent):
        temp_c = np.asarray(temp_c, dtype=float)
        rh_percent = np.asarray(rh_percent, dtype=float)
        a, b = 17.27, 237.7
        alpha = (a * temp_c) / (b + temp_c) + np.log(rh_percent / 100.0)
        dewpoint = (b * alpha) / (a - alpha)
        return dewpoint

    dewpoint_iso = dew_point(temp_iso, humid_iso)

    # Filter for levels above surface
    above_sfc_mask = geo_iso > geo_sfc

    # Build arrays including surface values (at 2m AGL)
    height_m_amsl = np.hstack([geo_iso[above_sfc_mask], np.array([geo_sfc + 2])])
    temp_c_amsl = np.hstack([temp_iso[above_sfc_mask], np.array([temp_agl])])
    dewpoint_c_amsl = np.hstack([dewpoint_iso[above_sfc_mask], np.array([dewpoint_sfc])])

    # Calculate Dry Adiabatic Lapse Rate (DALR) and Saturated Mixing Ratio (SMR)
    dalr = temp_c_amsl[-1] - 9.8 * ((height_m_amsl - height_m_amsl[-1]) / 1_000)
    smr = dewpoint_c_amsl[-1] - 2.0 * ((height_m_amsl - height_m_amsl[-1]) / 1_000)

    # Create the plot
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=temp_c_amsl, y=height_m_amsl, mode="lines", name="Temperature",
        line=dict(color="red", width=2)
    ))
    fig.add_trace(go.Scatter(
        x=dalr, y=height_m_amsl, mode="lines", name="DALR",
        line=dict(color="orange", width=2, dash="dash")
    ))
    fig.add_trace(go.Scatter(
        x=dewpoint_c_amsl, y=height_m_amsl, mode="lines", name="Dewpoint",
        line=dict(color="blue", width=2)
    ))
    fig.add_trace(go.Scatter(
        x=smr, y=height_m_amsl, mode="lines", name="SMR",
        line=dict(color="lightblue", width=2, dash="dash")
    ))

    fig.update_layout(
        title=f"Vertical Profile (Hour: {hour}:00)",
        xaxis_title="Temperature (°C)",
        yaxis_title="Height (m AMSL)",
        hovermode="y unified",
        width=600,
        height=600,
        autosize=False,
    )

    return fig


def neighbors_for_visualization(
    site_id,
    query_date,                 # date or "YYYY-MM-DD"
    val_df,
    feat_cols,
    site_indices,
    k: int = 5,
    site_col: str = "site_id",
    date_col: str = "date",
    label_col: str = "max_points",
):
    """
    Returns (meta_df, features_wide_df, features_long_df)

    meta_df: one row per (query + neighbor), with rank (0=query), date, label, distance
    features_wide_df: rows aligned with meta_df, columns are feat_cols
    features_long_df: long/tidy version -> columns: ['rank','which','feature','value']
                      where which ∈ {'query','candidate'}
    """
    # --- locate query row in validation set ---
    qdf = val_df[(val_df[site_col] == site_id) &
                 (val_df[date_col] == pd.Timestamp(query_date))]
    if qdf.empty:
        raise ValueError("Query day not found in validation set for this site.")

    model = site_indices.get(site_id)
    if model is None or len(model["Xn"]) == 0:
        raise ValueError("No train neighbors available for this site.")

    # --- build normalized query vector consistent with cosine search ---
    q_row = qdf.iloc[0]
    x = q_row[feat_cols].to_numpy(dtype=np.float32)
    x_n = x / (np.linalg.norm(x) + 1e-12)

    # --- run kNN (cap by available train points) ---
    nnb = min(k, len(model["Xn"]))
    dists, idxs = model["nn"].kneighbors(x_n.reshape(1, -1), n_neighbors=nnb, return_distance=True)
    idxs, dists = idxs[0], dists[0]

    # --- assemble metadata rows: rank=0 is the query itself ---
    rows_meta = []
    rows_feats = []

    # Query row (rank 0)
    q_label = int(q_row[label_col])
    q_date_print = pd.Timestamp(query_date).date()
    rows_meta.append({
        "rank": 0,
        "which": "query",
        "site_id": site_id,
        "date": q_date_print,
        "label": q_label,
        "distance": 0.0,
    })
    rows_feats.append(x.astype(np.float32))

    # Neighbor rows (ranks 1..nnb)
    for r, (j, d) in enumerate(zip(idxs, dists), start=1):
        # model['dates'] could be numpy.datetime64 or date → normalize to date
        dte = model['dates'][j]
        dte = pd.Timestamp(dte).date() if not isinstance(dte, pd.Timestamp) else dte.date()
        nb_label = int(model["labels"][j])
        rows_meta.append({
            "rank": r,
            "which": "candidate",
            "site_id": site_id,
            "date": dte,
            "label": nb_label,
            "distance": float(d),
        })
        # Use the *scaled* feature vector we searched with (not Xn, which is L2-normalized)
        rows_feats.append(model["features"][j].astype(np.float32))

    meta_df = pd.DataFrame(rows_meta)
    features_wide_df = pd.DataFrame(rows_feats, columns=feat_cols)
    # keep indexes aligned
    assert len(meta_df) == len(features_wide_df)

    # Long/tidy format for easy plotting (e.g., Altair)
    features_long_df = (
        features_wide_df
        .assign(rank=meta_df["rank"].values, which=meta_df["which"].values)
        .melt(id_vars=["rank", "which"], var_name="feature", value_name="value")
        .sort_values(["rank", "feature"], kind="stable")
        .reset_index(drop=True)
    )

    return meta_df, features_wide_df, features_long_df


