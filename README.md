# ❄️ Nepal Terai Cold Wave Forecasting System

An automated pipeline to monitor and predict Cold Wave events in the Nepal Plains (Terai) using **ECMWF (European Centre for Medium-Range Weather Forecasts)** Open Data and localized **DHM (Department of Hydrology and Meteorology)** observations.

## 🚀 Key Features
- **Temporal Alignment:** Custom resampling logic to match Nepal's meteorological day (08:45 AM NPT cutoff).
- **Automated Fetching:** Retrieves 3-hourly 2m Temperature data via ECMWF Open Data API.
- **Localized Logic:** Implements specific thresholds for "Cold Wave" (≤4°C) and "Severe Cold Wave" (≤2°C) based on regional standards.
- **Geospatial Selection:** Maps global GRIB2 data to specific station coordinates using nearest-neighbor interpolation.

## 🛠️ Tech Stack
- **Python 3.10+**
- **Xarray & cfgrib:** For processing high-dimensional meteorological GRIB2 files.
- **Pandas:** For time-series resampling and data manipulation.
- **ECMWF-opendata:** For cloud-based forecast retrieval.

## 📈 How It Works
The system captures the early morning temperature minimums (the coldest part of the day) by shifting the 24-hour window to align with Nepal's unique +5:45 offset. 



## 📋 Installation
1. Install system dependencies (for GRIB support):
   `brew install eccodes` (Mac) or `sudo apt-get install libeccodes-dev` (Ubuntu)
2. Install Python requirements:
   `pip install -r requirements.txt`
3. Run the analysis:
   `python run.py`