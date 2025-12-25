from pathlib import Path

# =========================
# PROJECT PATHS
# =========================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "outputs"

DATA_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# =========================
# INPUT / OUTPUT FILES
# =========================

EXCEL_PATH = DATA_DIR / "cold-wave-thresholds-terai.xlsx"
GRIB_PATH = DATA_DIR / "ifs_2t_latest.grib2"
OUTPUT_PATH = OUTPUT_DIR / "cold_wave_forecast_analysis.csv"

# =========================
# TIME / REGION SETTINGS
# =========================

LOCAL_TZ = "Asia/Kathmandu"

# =========================
# ECMWF FORECAST SETTINGS
# =========================

# 3-hourly up to 144h, then 6-hourly up to 240h
FORECAST_STEPS = list(range(0, 145, 3)) + list(range(150, 241, 6))

# =========================
# GEOGRAPHIC HEURISTICS
# =========================

LAT_SEPARATOR = 27.5  # Terai vs Hills
