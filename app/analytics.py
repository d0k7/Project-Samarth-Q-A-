# app/analytics.py
import pandas as pd
import numpy as np

def safe_cast_series(s):
    try:
        return pd.to_numeric(s, errors="coerce")
    except Exception:
        return s

def avg_annual_climate_metric(df_climate: pd.DataFrame, states: list, year_col_candidates=None, metric_candidates=None, last_n_years=3):
    """
    Compute average annual climate metric (e.g., annual_mean_temp_c) for the given states over last N years.
    The function tries to detect year column and a metric column from candidates.
    Returns (df_result, meta)
    """
    # auto-detect year column
    cols = [c.lower() for c in df_climate.columns]
    year_col = None
    for cand in (year_col_candidates or ["year", "yy", "yr"]):
        if cand in cols:
            year_col = df_climate.columns[cols.index(cand)]
            break
    if not year_col:
        raise ValueError("Could not detect year column in climate data")

    # metric detection
    metric_col = None
    possible_metrics = metric_candidates or ["annual_mean_temp_c", "annual_temp", "annual_mean_temp", "annual_rainfall_mm", "rainfall_mm", "mean_temp_c", "annual_mean_temp"]
    for cand in possible_metrics:
        if cand in cols:
            metric_col = df_climate.columns[cols.index(cand)]
            break

    if not metric_col:
        # fallback: pick numeric column other than year and state
        numeric_cols = df_climate.select_dtypes(include=[np.number]).columns.tolist()
        numeric_cols = [c for c in numeric_cols if c != year_col]
        if numeric_cols:
            metric_col = numeric_cols[0]
        else:
            raise ValueError("No numeric climate metric found")

    # state col detect
    state_col = None
    for cand in ["state", "region", "subdivision", "district"]:
        if cand in cols:
            state_col = df_climate.columns[cols.index(cand)]
            break

    max_year = int(pd.to_numeric(df_climate[year_col], errors="coerce").dropna().astype(int).max())
    min_year = max_year - last_n_years + 1
    df_climate[year_col] = pd.to_numeric(df_climate[year_col], errors="coerce")
    df_f = df_climate[(df_climate[year_col] >= min_year) & (df_climate[year_col] <= max_year)]
    if state_col:
        df_f = df_f[df_f[state_col].isin(states)]
        out = df_f.groupby(state_col)[metric_col].mean().reset_index().rename(columns={metric_col: f"avg_{metric_col}"})
    else:
        out = pd.DataFrame({f"avg_{metric_col}": [df_f[metric_col].mean()]})
    return out, {"years_used": (min_year, max_year), "metric_column": metric_col, "year_column": year_col, "state_column": state_col}

def top_crops_by_volume(df_crop: pd.DataFrame, state: str, last_n_years:int, top_m:int):
    # try to detect standard columns
    df = df_crop.copy()
    cols_lower = [c.lower() for c in df.columns]
    # detect year column
    year_col = None
    for cand in ["year", "season", "reporting_year"]:
        if cand in cols_lower:
            year_col = df.columns[cols_lower.index(cand)]
            break
    # detect production column
    prod_col = None
    for cand in ["production_tonnes", "production", "production (tonnes)", "production (t)","quantity"]:
        if cand in cols_lower:
            prod_col = df.columns[cols_lower.index(cand)]
            break
    # detect state, crop columns
    state_col = None
    for cand in ["state", "st", "state_name"]:
        if cand in cols_lower:
            state_col = df.columns[cols_lower.index(cand)]
            break
    crop_col = None
    for cand in ["crop", "commodity", "crop_name"]:
        if cand in cols_lower:
            crop_col = df.columns[cols_lower.index(cand)]
            break

    # fallback names
    year_col = year_col or "year"
    prod_col = prod_col or "production_tonnes"
    state_col = state_col or "state"
    crop_col = crop_col or "crop"

    # coerce types
    if year_col in df.columns:
        df[year_col] = pd.to_numeric(df[year_col], errors="coerce")
        max_year = int(df[year_col].dropna().astype(int).max()) if df[year_col].dropna().size>0 else None
    else:
        max_year = None

    if max_year:
        min_year = max_year - last_n_years + 1
        df = df[(df[year_col] >= min_year) & (df[year_col] <= max_year)]
    # filter by state if present
    if state_col in df.columns:
        dff = df[df[state_col] == state]
    else:
        dff = df

    # ensure production numeric
    if prod_col in dff.columns:
        dff[prod_col] = pd.to_numeric(dff[prod_col], errors="coerce").fillna(0)
    else:
        dff[prod_col] = 0

    agg = dff.groupby(crop_col)[prod_col].sum().reset_index().sort_values(prod_col, ascending=False)
    return agg.head(top_m)

def production_trend(df_crop: pd.DataFrame, crop_name: str, region_filter: dict = None):
    # collapse to yearly totals for a crop
    df = df_crop.copy()
    cols_lower = [c.lower() for c in df.columns]
    # detect columns
    year_col = None
    for cand in ["year", "season"]:
        if cand in cols_lower:
            year_col = df.columns[cols_lower.index(cand)]
            break
    if not year_col:
        df["year"] = pd.NaT
        year_col = "year"
    crop_col = None
    for cand in ["crop", "commodity"]:
        if cand in cols_lower:
            crop_col = df.columns[cols_lower.index(cand)]
            break
    if not crop_col:
        crop_col = "crop"
    prod_col = None
    for cand in ["production_tonnes", "production"]:
        if cand in cols_lower:
            prod_col = df.columns[cols_lower.index(cand)]
            break
    prod_col = prod_col or "production_tonnes"
    df[prod_col] = pd.to_numeric(df.get(prod_col, 0), errors="coerce").fillna(0)
    # filter crop
    dff = df[df[crop_col].astype(str).str.lower() == crop_name.lower()].copy()
    if region_filter:
        for k, v in region_filter.items():
            if k in dff.columns:
                dff = dff[dff[k] == v]
    # group
    if year_col in dff.columns:
        dff[year_col] = pd.to_numeric(dff[year_col], errors="coerce")
        ts = dff.groupby(year_col)[prod_col].sum().reset_index().dropna()
    else:
        ts = pd.DataFrame([[0, dff[prod_col].sum()]], columns=["year", prod_col])
    # linear trend
    if len(ts) >= 2:
        x = ts["year"].astype(float).values
        y = ts[prod_col].astype(float).values
        A = np.vstack([x, np.ones(len(x))]).T
        m, c = np.linalg.lstsq(A, y, rcond=None)[0]
    else:
        m, c = 0.0, float(ts[prod_col].sum() or 0)
    return ts.rename(columns={prod_col: "production_tonnes"}), {"slope_per_year": float(m), "intercept": float(c)}

def correlate_production_with_climate(df_prod: pd.DataFrame, df_climate: pd.DataFrame, crop_name: str, state: str, last_n_years:int):
    # produce annual production sums and merge with climate metric per year, then compute Pearson
    ts_prod, _ = production_trend(df_prod, crop_name, region_filter={"state": state})
    # get climate metric
    try:
        climate_out, meta = avg_annual_climate_metric(df_climate, [state], last_n_years=last_n_years)
        metric = meta["metric_column"]
        # need year-level climate per year for correlation; fallback: try to pivot df_climate to year->metric
        # if df_climate has a 'year' column and state column we can get yearwise metric
        cols_lower = [c.lower() for c in df_climate.columns]
        year_col = df_climate.columns[cols_lower.index("year")] if "year" in cols_lower else None
        state_col = df_climate.columns[cols_lower.index("state")] if "state" in cols_lower else None
        if year_col and state_col and metric in df_climate.columns:
            cagg = df_climate[df_climate[state_col] == state].groupby(year_col)[metric].mean().reset_index().rename(columns={metric: metric})
            merged = pd.merge(ts_prod, cagg, left_on="year", right_on=year_col, how="inner")
            corr = float(merged["production_tonnes"].corr(merged[metric])) if len(merged)>=2 else None
            return merged, {"pearson_corr": corr, "climate_metric": metric}
    except Exception:
        pass
    return pd.DataFrame(), {"pearson_corr": None}
