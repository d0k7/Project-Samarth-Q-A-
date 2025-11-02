# scripts/diagnose_data.py
# =========================================================
# diagnose_data.py — robust data inspection helper
# =========================================================

# --- PATH FIX (must be first) ---
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# --- IMPORTS ---
import json
import pandas as pd
from pprint import pprint
from app.loaders import load_crop_production, load_climate_temp_series, load_yield_all_india

# --- UTILITIES ---
def unwrap_loader(ret):
    """Loader may return df or (df, meta). Return (df, meta)."""
    if ret is None:
        return None, {}
    if isinstance(ret, tuple) and len(ret) >= 1:
        # common pattern: (df, meta)
        df = ret[0]
        meta = ret[1] if len(ret) > 1 else {}
        return df, (meta or {})
    # otherwise assume it's a dataframe-like
    return ret, {}

def column_info(df, n_sample=6):
    if df is None:
        return []
    info = []
    for c in df.columns:
        dtype = str(df[c].dtype)
        nnull = int(df[c].notna().sum())
        sample = df[c].dropna().astype(str).unique()[:n_sample].tolist()
        info.append({"col": c, "dtype": dtype, "non_null": nnull, "sample_values": sample})
    return info

def detect_year_columns(df):
    if df is None:
        return []
    years = []
    for c in df.columns:
        try:
            numeric = pd.to_numeric(df[c], errors="coerce")
            if numeric.dropna().shape[0] >= 3:
                mn = numeric.min(); mx = numeric.max()
                if mn >= 1800 and mx <= 2100:
                    years.append({"col": c, "min": int(mn), "max": int(mx)})
        except Exception:
            pass
    return years

def detect_state_like_columns(df, max_samples=20):
    if df is None:
        return []
    cand = []
    for c in df.columns:
        vals = df[c].dropna().astype(str).unique()[:max_samples]
        alpha_count = sum(1 for v in vals if any(ch.isalpha() for ch in v))
        # If most samples contain letters and lengths are reasonable, consider it state-like
        if alpha_count >= 1 and all(len(str(v)) < 80 for v in vals):
            cand.append({"col": c, "sample_values": vals[:8].tolist()})
    return cand

def safe_print(title, obj=None):
    sep = "=" * 8
    print(f"\n{sep} {title} {sep}")
    if obj is None:
        return
    if isinstance(obj, (str, int, float)):
        print(obj)
    else:
        try:
            print(json.dumps(obj, indent=2, default=str))
        except Exception:
            pprint(obj)

# --- MAIN ---
def inspect_loader(fn, name):
    try:
        ret = fn()
    except TypeError:
        # some loaders require no args; try calling with None
        try:
            ret = fn(None)
        except Exception as e:
            return {"error": str(e)}
    except Exception as e:
        return {"error": str(e)}

    df, meta = unwrap_loader(ret)
    out = {"meta": meta}
    if df is None:
        out["status"] = "no dataframe returned"
        return out

    try:
        out["rows"] = int(df.shape[0])
        out["cols"] = int(df.shape[1])
    except Exception:
        out["rows"] = None
        out["cols"] = None

    out["columns_info"] = column_info(df)
    out["head"] = df.head(5).to_dict(orient="records")
    out["candidate_years"] = detect_year_columns(df)
    out["candidate_state_cols"] = detect_state_like_columns(df)
    return out

def main():
    print("Working dir:", os.getcwd())
    print("Python:", sys.executable)

    # Crop
    crop_result = inspect_loader(load_crop_production, "crop_production")
    safe_print("CROP DATA SOURCE / DIAGNOSIS", crop_result)

    # Climate
    climate_result = inspect_loader(load_climate_temp_series, "climate_series")
    safe_print("CLIMATE DATA SOURCE / DIAGNOSIS", climate_result)

    # All-India yield (optional)
    yield_result = inspect_loader(load_yield_all_india, "yield_all_india")
    safe_print("YIELD (ALL INDIA) DATA SOURCE / DIAGNOSIS", yield_result)

    print("\n=== Diagnostics complete ===")
    print("Copy the full output and paste here so I can prepare exact loader/analytics mappings.")

if __name__ == "__main__":
    main()
