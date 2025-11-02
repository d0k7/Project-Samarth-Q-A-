# app/loaders.py
import os
import re
import pandas as pd
from .config import DATA_DIR

def _find_file_contains(substr):
    substr = substr.lower()
    for fname in os.listdir(DATA_DIR):
        if substr in fname.lower():
            return os.path.join(DATA_DIR, fname)
    return None

def _read_csv_safe(path, **kwargs):
    try:
        return pd.read_csv(path, low_memory=False, **kwargs)
    except Exception:
        return pd.read_csv(path, encoding="latin1", low_memory=False, **kwargs)

def load_crop_production():
    """
    Load the national/wide crop production CSV and normalize to long form:
    returns (df, meta) where df has columns: ['year', 'crop', 'production_tonnes', ...]
    """
    path = _find_file_contains("crop-wise details of production")
    if not path:
        # fallback sample
        df = pd.DataFrame([
            {"year": 2019, "state": "StateA", "district": "D1", "crop": "Wheat", "production_tonnes": 1300},
            {"year": 2019, "state": "StateB", "district": "D2", "crop": "Rice", "production_tonnes": 2000},
        ])
        return df, {"source_file": "sample_crop_production", "full_path": None}

    raw = _read_csv_safe(path)
    raw.columns = [c.strip() for c in raw.columns]

    # attempt to find the crop/name column
    crop_col = None
    for cand in ["Crops", "Crop", "crop", "Crop Name", "Crop_Name"]:
        if cand in raw.columns:
            crop_col = cand
            break

    # find columns that denote production with pattern like '2016-17 - Production'
    prod_cols = [c for c in raw.columns if re.search(r"\d{4}[-–]\d{2}\s*-\s*Production", c, flags=re.I)]
    # also accept columns that end with ' - Production' or contain 'Production'
    if not prod_cols:
        prod_cols = [c for c in raw.columns if "production" in c.lower()]

    # If found, melt to long format
    if prod_cols and crop_col:
        melt = raw[[crop_col] + prod_cols].melt(id_vars=[crop_col], value_vars=prod_cols,
                                                var_name="year_col", value_name="production_tonnes")
        # extract year from year_col (take first 4 digits as start year)
        def parse_year(s):
            m = re.search(r"(\d{4})[-–](\d{2})", s)
            if m:
                return int(m.group(1))  # choose start year
            # fallback: first 4 digits anywhere
            m2 = re.search(r"(\d{4})", s)
            return int(m2.group(1)) if m2 else None
        melt["year"] = melt["year_col"].apply(parse_year)
        melt = melt.rename(columns={crop_col: "crop"})
        melt["production_tonnes"] = pd.to_numeric(melt["production_tonnes"], errors="coerce").fillna(0)
        df_out = melt[["year", "crop", "production_tonnes"]].sort_values(["crop", "year"]).reset_index(drop=True)
        return df_out, {"source_file": os.path.basename(path), "full_path": path}

    # If not the expected wide format, try to guess a tidy table already present:
    # look for columns like 'Year', 'state', 'crop', 'production'
    candidates = raw.copy()
    cols_lower = [c.lower() for c in candidates.columns]
    if any(x in cols_lower for x in ("production", "production_tonnes", "quantity")):
        # try to normalize names
        rename_map = {}
        for c in candidates.columns:
            if c.lower() in ("production", "production (tonnes)", "production_tonnes"):
                rename_map[c] = "production_tonnes"
            if c.lower() in ("crop", "crops", "commodity", "crop_name"):
                rename_map[c] = "crop"
            if c.lower() in ("year", "season"):
                rename_map[c] = "year"
            if c.lower() in ("state", "state_name"):
                rename_map[c] = "state"
        candidates = candidates.rename(columns=rename_map)
        if "production_tonnes" in candidates.columns:
            candidates["production_tonnes"] = pd.to_numeric(candidates["production_tonnes"], errors="coerce").fillna(0)
            return candidates, {"source_file": os.path.basename(path), "full_path": path}

    # fallback: return raw as-is (caller will handle)
    return raw, {"source_file": os.path.basename(path), "full_path": path}

def load_climate_temp_series():
    """
    Load the climate CSV and return a simplified table:
    columns: ['year', 'annual_mean_temp_c'] (national series if no state present)
    """
    path = _find_file_contains("seasonal and annual minmax") or _find_file_contains("year-wise climate risk")
    if not path:
        # fallback sample
        df = pd.DataFrame([
            {"year": 2018, "annual_mean_temp_c": 26.5},
            {"year": 2019, "annual_mean_temp_c": 26.8},
        ])
        return df, {"source_file": "sample_climate", "full_path": None}

    raw = _read_csv_safe(path)
    raw.columns = [c.strip() for c in raw.columns]
    cols_lower = [c.lower() for c in raw.columns]

    # detect year column
    year_col = None
    for cand in ("year", "YEAR", "Year"):
        if cand in raw.columns:
            year_col = cand
            break
    if not year_col:
        # try any numeric-looking column
        for c in raw.columns:
            try:
                if pd.to_numeric(raw[c], errors="coerce").dropna().shape[0] > 3:
                    year_col = c
                    break
            except Exception:
                pass

    # detect annual min/max
    min_col = next((c for c in raw.columns if "annual - min" in c.lower()), None)
    max_col = next((c for c in raw.columns if "annual - max" in c.lower()), None)

    if year_col and (min_col or max_col):
        if min_col and max_col:
            raw["annual_mean_temp_c"] = (pd.to_numeric(raw[min_col], errors="coerce") +
                                         pd.to_numeric(raw[max_col], errors="coerce")) / 2.0
        else:
            # if only one of them present, use that as proxy
            col = min_col or max_col
            raw["annual_mean_temp_c"] = pd.to_numeric(raw[col], errors="coerce")
        out = raw.rename(columns={year_col: "year"})[["year", "annual_mean_temp_c"]].dropna(subset=["year"])
        out["year"] = pd.to_numeric(out["year"], errors="coerce").astype(int)
        return out.reset_index(drop=True), {"source_file": os.path.basename(path), "full_path": path}

    # If climate file is differently structured (e.g., state-wise), return full dataframe and meta
    return raw, {"source_file": os.path.basename(path), "full_path": path}

def load_yield_all_india():
    """
    Load All-India yield CSV and normalize to long form: columns ['year', 'crop', 'yield_kg_per_ha']
    """
    path = _find_file_contains("all india level yield")
    if not path:
        return pd.DataFrame(), {"source_file": "sample_yield", "full_path": None}

    raw = _read_csv_safe(path)
    raw.columns = [c.strip() for c in raw.columns]

    # Year column often like '2014-15' - extract first 4 digits
    if "Year" in raw.columns:
        # melt other crop columns (e.g., Rice, Wheat) to long form
        value_cols = [c for c in raw.columns if c != "Year"]
        df_long = raw.melt(id_vars=["Year"], value_vars=value_cols, var_name="crop", value_name="yield_kg_per_ha")
        def yr_to_int(s):
            m = re.search(r"(\d{4})", str(s))
            return int(m.group(1)) if m else None
        df_long["year"] = df_long["Year"].apply(yr_to_int)
        df_long["yield_kg_per_ha"] = pd.to_numeric(df_long["yield_kg_per_ha"], errors="coerce")
        df_long = df_long[["year", "crop", "yield_kg_per_ha"]].dropna(subset=["year"])
        return df_long.reset_index(drop=True), {"source_file": os.path.basename(path), "full_path": path}

    # fallback: return raw
    return raw, {"source_file": os.path.basename(path), "full_path": path}
