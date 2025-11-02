from app.analytics import avg_annual_rainfall, top_crops_by_volume
from app.loaders import load_crop_production, load_rainfall

def test_avg_rain_smoke():
    df = load_rainfall()
    res, meta = avg_annual_rainfall(df, ["StateA", "StateB"], 2)
    assert "avg_annual_rainfall_mm" in res.columns

def test_top_crops_smoke():
    df = load_crop_production()
    top = top_crops_by_volume(df, "StateA", 2, 2)
    assert "crop" in top.columns
