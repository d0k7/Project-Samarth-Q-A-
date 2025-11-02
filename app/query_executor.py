# app/query_executor.py
import re
import pandas as pd
import traceback
from .loaders import load_crop_production, load_climate_temp_series, load_yield_all_india
from .utils import fig_to_base64
import matplotlib.pyplot as plt

def _unwrap_loader_result(ret):
    """Accept either df or (df, meta) and return (df, meta_dict)."""
    if isinstance(ret, tuple) and len(ret) >= 1:
        df = ret[0]
        meta = ret[1] if len(ret) > 1 else {}
        return df, (meta or {})
    else:
        return ret, {}

def parse_question(question: str):
    raw = (question or "").strip()
    q = raw.lower()
    n_match = re.search(r"last\s+(\d+)\s+(?:years|year)", q)
    N = int(n_match.group(1)) if n_match else 5
    m_match = re.search(r"top\s+(\d+)", q)
    M = int(m_match.group(1)) if m_match else 3
    return {"raw": raw, "N": N, "M": M}

def _normalize_columns(df: pd.DataFrame):
    """
    Return a mapping of normalized_column -> original_column_name and a DataFrame view
    where columns are normalized (lowercase, punctuation -> single space).
    """
    def norm(s):
        if s is None:
            return ""
        s = str(s)
        s = s.strip()
        # replace punctuation with space, collapse spaces, lowercase
        s = re.sub(r"[-_/\\(),]+", " ", s)
        s = re.sub(r"\s+", " ", s)
        return s.lower()
    col_map = {norm(c): c for c in df.columns}
    df_norm = df.rename(columns={orig: norm(orig) for orig in df.columns})
    return df_norm, col_map

def _is_year_like_series(s: pd.Series):
    """Return True if series looks like years (numeric values between 1800 and 2100)."""
    try:
        nums = pd.to_numeric(s, errors="coerce").dropna()
        if nums.shape[0] < 3:
            return False
        mn, mx = int(nums.min()), int(nums.max())
        return 1800 <= mn <= mx <= 2100
    except Exception:
        return False

def _find_annual_min_max_candidates(df_norm: pd.DataFrame):
    """
    Return pair (min_col_norm, max_col_norm) using token heuristics.
    """
    min_col = None
    max_col = None
    for nc in df_norm.columns:
        if "annual" in nc and "min" in nc:
            min_col = nc
        if "annual" in nc and "max" in nc:
            max_col = nc
    # if not found, try combinations: any col with 'min' and any with 'max'
    if not min_col:
        for nc in df_norm.columns:
            if "min" in nc and ("temp" in nc or "temperature" in nc or "deg" in nc):
                min_col = nc
                break
    if not max_col:
        for nc in df_norm.columns:
            if "max" in nc and ("temp" in nc or "temperature" in nc or "deg" in nc):
                max_col = nc
                break
    return min_col, max_col

def _fallback_numeric_pair(df_norm: pd.DataFrame):
    """
    If no explicit min/max columns found, try to find numeric columns that look like min/max
    but IGNORE year-like columns. Return (min_col_norm, max_col_norm).
    If exactly one plausible numeric (temperature-like) column exists, return (that_col, None)
    so that code will use it directly as the annual metric (no averaging with year).
    """
    numeric_cols = []
    for nc in df_norm.columns:
        # skip obvious year-like names
        if "year" in nc:
            continue
        try:
            nums = pd.to_numeric(df_norm[nc], errors="coerce").dropna()
            if nums.shape[0] >= 3:
                mean_val = float(nums.mean())
                # heuristics: temperature-like mean in a plausible range (-60..80)
                if -60.0 <= mean_val <= 80.0:
                    numeric_cols.append((nc, mean_val))
        except Exception:
            pass
    if len(numeric_cols) == 1:
        # single plausible numeric column: use as annual_mean (no averaging with year)
        return numeric_cols[0][0], None
    if len(numeric_cols) >= 2:
        numeric_cols.sort(key=lambda x: x[1])
        return numeric_cols[0][0], numeric_cols[-1][0]
    return None, None

def _compute_national_climate_avg(df_clim_raw, last_n_years: int):
    """
    Robust detection of YEAR and annual min/max columns.
    Returns (climate_out_df, meta) or (None, {}).
    meta contains years_used, rows_used, original column names, and helpful debug fields.
    """
    meta_debug = {"columns_sample": None, "rows_sample": None, "detection_notes": []}

    if df_clim_raw is None:
        meta_debug["detection_notes"].append("climate loader returned None")
        return None, meta_debug

    if not isinstance(df_clim_raw, pd.DataFrame):
        meta_debug["detection_notes"].append("climate loader did not return a DataFrame")
        return None, meta_debug

    if df_clim_raw.empty:
        meta_debug["detection_notes"].append("climate DataFrame empty")
        meta_debug["columns_sample"] = list(df_clim_raw.columns)
        return None, meta_debug

    # sample columns & rows (for provenance)
    try:
        meta_debug["columns_sample"] = list(df_clim_raw.columns)
        meta_debug["rows_sample"] = df_clim_raw.head(10).fillna("").to_dict(orient="records")
    except Exception:
        meta_debug["columns_sample"] = list(df_clim_raw.columns)

    # normalize columns for detection
    df_norm, col_map = _normalize_columns(df_clim_raw)

    # find year column normalized
    year_col_norm = None
    if "year" in df_norm.columns:
        year_col_norm = "year"
    else:
        for nc in df_norm.columns:
            if nc.strip() == "year":
                year_col_norm = nc
                break
    if year_col_norm is None:
        # fallback: numeric-like column that looks like years
        for nc in df_norm.columns:
            try:
                if _is_year_like_series(df_norm[nc]):
                    year_col_norm = nc
                    meta_debug["detection_notes"].append(f"Using numeric-like column '{nc}' as year")
                    break
            except Exception:
                pass

    if year_col_norm is None:
        meta_debug["detection_notes"].append("No year-like column found")
        return None, meta_debug

    # find annual min/max normalized column names
    min_col_norm, max_col_norm = _find_annual_min_max_candidates(df_norm)
    if not min_col_norm and not max_col_norm:
        meta_debug["detection_notes"].append("No 'annual min/max' tokens found — trying numeric fallback")
        min_col_norm, max_col_norm = _fallback_numeric_pair(df_norm)

    if not min_col_norm and not max_col_norm:
        meta_debug["detection_notes"].append("No candidate min/max columns found even after fallback")
        return None, meta_debug

    # map normalized back to original names
    year_col_orig = col_map.get(year_col_norm, year_col_norm)
    min_col_orig = col_map.get(min_col_norm) if min_col_norm else None
    max_col_orig = col_map.get(max_col_norm) if max_col_norm else None

    # Prepare working dataframe and coerce numeric
    df_work = df_clim_raw.copy()
    df_work[year_col_orig] = pd.to_numeric(df_work[year_col_orig], errors="coerce")
    if min_col_orig and max_col_orig:
        # both present -> average them
        df_work["annual_mean_temp_c"] = (pd.to_numeric(df_work[min_col_orig], errors="coerce") + pd.to_numeric(df_work[max_col_orig], errors="coerce")) / 2.0
    else:
        # single candidate -> use it directly as the metric
        use_col = min_col_orig or max_col_orig
        df_work["annual_mean_temp_c"] = pd.to_numeric(df_work[use_col], errors="coerce")

    # ensure there are numeric year values
    if df_work[year_col_orig].dropna().empty:
        meta_debug["detection_notes"].append(f"Year column '{year_col_orig}' could not be coerced to numeric")
        return None, meta_debug

    max_year = int(df_work[year_col_orig].dropna().astype(int).max())
    min_year = int(max_year - last_n_years + 1)
    sel = df_work[(df_work[year_col_orig] >= min_year) & (df_work[year_col_orig] <= max_year)]
    if sel.empty:
        meta_debug["detection_notes"].append(f"No rows in year range {min_year}..{max_year}")
        available_years = df_work[year_col_orig].dropna().astype(int).unique().tolist()
        meta_debug["available_years_sample"] = available_years[:10]
        return None, meta_debug

    avg_val = float(sel["annual_mean_temp_c"].mean())
    rows_used = sel[[year_col_orig, "annual_mean_temp_c"]].dropna().rename(columns={year_col_orig: "year"}).to_dict(orient="records")
    out = pd.DataFrame([{"region": "All India", "avg_annual_mean_temp_c": avg_val}])
    meta = {
        "years_used": (min_year, max_year),
        "year_column": year_col_orig,
        "min_col": min_col_orig,
        "max_col": max_col_orig,
        "rows_used": rows_used,
        "debug": meta_debug
    }
    return out, meta

def exec_compare_rainfall_and_top_crops(parsed):
    N = parsed.get("N", 5)
    M = parsed.get("M", 3)

    # load crop and climate - loaders may return (df, meta) or df
    try:
        ret_crop = load_crop_production()
        df_crop, meta_crop = _unwrap_loader_result(ret_crop)
    except Exception:
        df_crop, meta_crop = None, {}

    try:
        ret_clim = load_climate_temp_series()
        df_clim, meta_clim = _unwrap_loader_result(ret_clim)
    except Exception:
        df_clim, meta_clim = None, {}

    # climate: robust national average detection
    climate_out, climate_meta = None, {}
    try:
        climate_out, climate_meta = _compute_national_climate_avg(df_clim, N)
    except Exception:
        climate_out, climate_meta = None, {"debug": "exception during detection"}

    # top crops (All India aggregation)
    top_per_state = {}
    crop_sample_rows = []
    try:
        if isinstance(df_crop, pd.DataFrame):
            # find production-like and crop-like columns (case-insensitive)
            cols_l = {c.lower(): c for c in df_crop.columns}
            prod_col = next((orig for low, orig in cols_l.items() if "production" in low or "quantity" in low or "tonne" in low), None)
            crop_col = next((orig for low, orig in cols_l.items() if low in ("crop","crops","commodity","crops name","cropsname","crops ")), None)
            year_col = next((orig for low, orig in cols_l.items() if low in ("year","season","financial_year","year ")), None)

            dff = df_crop.copy()
            if year_col:
                dff[year_col] = pd.to_numeric(dff[year_col], errors="coerce")
                if not dff[year_col].dropna().empty:
                    maxy = int(dff[year_col].dropna().astype(int).max())
                    dff = dff[(dff[year_col] >= (maxy - N + 1)) & (dff[year_col] <= maxy)]

            if prod_col and crop_col:
                dff[prod_col] = pd.to_numeric(dff[prod_col], errors="coerce").fillna(0)
                agg = dff.groupby(crop_col)[prod_col].sum().reset_index().sort_values(prod_col, ascending=False).head(M)
                agg = agg.rename(columns={crop_col: "crop", prod_col: "production_tonnes"})
                top_per_state["All India"] = agg.to_dict(orient="records")
                crop_sample_rows = dff.head(8).to_dict(orient="records")
            else:
                # fallback: try to sum numeric columns if there's a 'Crops' column
                if "Crops" in df_crop.columns:
                    numeric_cols = [c for c in df_crop.columns if pd.api.types.is_numeric_dtype(df_crop[c])]
                    if numeric_cols:
                        df_sum = df_crop.copy()
                        df_sum["production_tonnes"] = df_sum[numeric_cols].sum(axis=1)
                        agg = df_sum.groupby("Crops")["production_tonnes"].sum().reset_index().sort_values("production_tonnes", ascending=False).head(M)
                        agg = agg.rename(columns={"Crops": "crop"})
                        top_per_state["All India"] = agg.to_dict(orient="records")
                        crop_sample_rows = df_sum.head(8).to_dict(orient="records")
                    else:
                        top_per_state["All India"] = []
                else:
                    top_per_state["All India"] = []
        else:
            top_per_state["All India"] = []
    except Exception:
        top_per_state["All India"] = []

    # chart (optional)
    chart_b64 = None
    try:
        if climate_out is not None and not climate_out.empty:
            fig, ax = plt.subplots()
            ycol = next((c for c in climate_out.columns if c != "region"), climate_out.columns[-1])
            ax.bar(climate_out["region"].astype(str), climate_out[ycol].astype(float))
            ax.set_ylabel("Avg annual mean (°C)")
            ax.set_title(f"Average annual climate metric ({climate_meta.get('years_used')})")
            chart_b64 = fig_to_base64(fig)
    except Exception:
        chart_b64 = None

    # build textual answer
    lines = []
    if climate_out is not None and not climate_out.empty:
        years_used = climate_meta.get("years_used")
        lines.append(f"Average climate metric (detected) over last {N} years:")
        for _, r in climate_out.iterrows():
            val_col = next((c for c in climate_out.columns if c != "region"), climate_out.columns[-1])
            try:
                lines.append(f" - {r.get('region','All India')}: {float(r[val_col]):.2f} (avg over {years_used})")
            except Exception:
                lines.append(f" - {r.get('region','All India')}: {r[val_col]}")
    else:
        lines.append("No climate metric could be computed from local climate files.")

    lines.append("")  # spacer
    for region_label, items in top_per_state.items():
        lines.append(f"Top {M} crops in {region_label} (by total production over last {N} years):")
        if items:
            for it in items:
                name = it.get("crop") or it.get("Crops") or next(iter(it.keys()), "(unknown)")
                prod = it.get("production_tonnes") or it.get("Production") or it.get("production")
                lines.append(f" - {name}: {prod}")
        else:
            lines.append(" - (no data)")

    # provenance: include sources, sample rows and columns and debug if detection failed
    prov = []
    prov.append({
        "dataset": (meta_crop.get("source_file") if isinstance(meta_crop, dict) else None),
        "path": (meta_crop.get("full_path") if isinstance(meta_crop, dict) else None),
        "sample_rows_used": crop_sample_rows
    })
    prov.append({
        "dataset": (meta_clim.get("source_file") if isinstance(meta_clim, dict) else None),
        "path": (meta_clim.get("full_path") if isinstance(meta_clim, dict) else None),
        "years_used": climate_meta.get("years_used") if isinstance(climate_meta, dict) else None,
        "rows_used": climate_meta.get("rows_used") if isinstance(climate_meta, dict) else [],
        "columns_sample": (climate_meta.get("debug", {}).get("columns_sample") if isinstance(climate_meta.get("debug", {}), dict) else climate_meta.get("debug", {}).get("columns_sample")),
        "rows_sample": (climate_meta.get("debug", {}).get("rows_sample") if isinstance(climate_meta.get("debug", {}), dict) else climate_meta.get("debug", {}).get("rows_sample")),
        "detection_notes": (climate_meta.get("debug", {}).get("detection_notes") if isinstance(climate_meta.get("debug", {}), dict) else None),
        "available_years_sample": climate_meta.get("debug", {}).get("available_years_sample") if isinstance(climate_meta.get("debug", {}), dict) else None
    })

    return {
        "answer_text": "\n".join(lines),
        "chart": chart_b64,
        "climate_table": (climate_out.to_dict(orient="records") if climate_out is not None else []),
        "top_crops": top_per_state,
        "provenance": prov
    }

def handle_question(question: str):
    try:
        if not question or not question.strip():
            return {"answer_text": "Please enter a non-empty question.", "chart": None, "climate_table": [], "top_crops": {}, "provenance": []}
        q = question.strip().lower()
        parsed = parse_question(question)
        if "list states" in q:
            # attempt to find a 'state' column in crop or climate files
            states = []
            try:
                df_crop, _ = _unwrap_loader_result(load_crop_production())
                if isinstance(df_crop, pd.DataFrame):
                    for c in df_crop.columns:
                        if c.lower() == "state":
                            states = df_crop[c].dropna().astype(str).unique().tolist()
                            break
            except Exception:
                pass
            if not states:
                states = ["All India"]
            return {"answer_text": "Detected states from local data: " + ", ".join(states), "chart": None, "climate_table": [], "top_crops": {}, "provenance": []}
        if re.search(r"\b(compare|contrast)\b", q) or True:
            return exec_compare_rainfall_and_top_crops(parsed)
        return {"answer_text": "Sorry — couldn't classify", "chart": None, "climate_table": [], "top_crops": {}, "provenance": []}
    except Exception as e:
        tb = traceback.format_exc()
        return {"answer_text": f"Internal error: {e}", "debug": tb, "chart": None, "climate_table": [], "top_crops": {}, "provenance": []}
