import numpy as np
import pandas as pd
import xarray as xr
import json
import sys
from pathlib import Path
from datetime import datetime
from src.api.dhm_scraper import fetch_dhm_temperature
from src.api.ecmwf_fetch import fetch_forecast
from src.config import (
    OUTPUT_PATH,
    GRIB_PATH,
    LOCAL_TZ
)

# ------------------------------------------------------------------
# 1. Cold Wave Logic (Nepal Terai/Plains Standards)
# ------------------------------------------------------------------

def evaluate_forecast_cold_wave(min_temps):
    """
    Evaluates 2-consecutive-day thresholds:
    - Possible Severe Cold Wave: Tmin <= 2°C for 2 days
    - Possible Cold Wave: Tmin <= 4°C for 2 days
    """
    cw_streak = 0
    scw_streak = 0

    for tmin in min_temps:
        if pd.isna(tmin):
            cw_streak = 0
            scw_streak = 0
            continue

        if tmin <= 2.0:
            scw_streak += 1
            cw_streak += 1
        elif tmin <= 4.0:
            scw_streak = 0
            cw_streak += 1
        else:
            scw_streak = 0
            cw_streak = 0

        if scw_streak >= 2:
            return "Possible Severe Cold Wave"
        if cw_streak >= 2:
            return "Possible Cold Wave"

    return "No Cold Wave Signal"

# ----------------------------------------------------
# Main Execution Flow
# ----------------------------------------------------

def main():
    # Step 1: Load station metadata
    print("Loading stations from JSON...")
    try:
        with open("data/stations.json") as f:
            stations_data = json.load(f)
        stations_df = pd.DataFrame(stations_data)
    except FileNotFoundError:
        print("Error: data/stations.json not found.")
        return

    # Step 2: Fetch ECMWF forecast
    fetch_forecast()

    # Step 3: Fetch DHM observed data
    print("Fetching DHM observed station data...")
    dhm_df = fetch_dhm_temperature()

    # Step 4: Merge Metadata with DHM Observations
    df = pd.merge(
        stations_df,
        dhm_df.rename(
            columns={
                "lat": "dhm_lat",
                "lon": "dhm_lon",
                "t_min": "DHM_Min",
                "t_max": "DHM_Max",
            }
        ),
        how="left",
        on="station",
    )

    # Step 5: Open ECMWF GRIB
    print("Opening ECMWF GRIB...")
    if not GRIB_PATH.exists():
        print(f"Error: GRIB file not found at {GRIB_PATH}")
        return

    try:
        ds = xr.open_dataset(
            GRIB_PATH, 
            engine="cfgrib", 
            backend_kwargs={'filter_by_keys': {'typeOfLevel': 'heightAboveGround'}}
        )
    except Exception as e:
        print(f"Filtered load failed: {e}")
        ds = xr.open_dataset(GRIB_PATH, engine="cfgrib")

    if "t2m" in ds:
        var_name = "t2m"
    elif "2t" in ds:
        var_name = "2t"
    else:
        available = list(ds.data_vars)
        if not available:
            print("❌ No variables found in GRIB.")
            return
        var_name = available[0]

    print(f"Using forecast variable: {var_name}")
    t2m = ds[var_name]

    # Step 6: Process each station
    results = []
    print(f"Processing {len(df)} stations...")

    for _, row in df.iterrows():
        try:
            station_name = row["station"]
            lat = float(row["lat"])
            lon = float(row["lon"])

            try:
                t2m_point = t2m.sel(latitude=lat, longitude=lon % 360, method="nearest")
            except KeyError:
                t2m_point = t2m.sel(lat=lat, lon=lon % 360, method="nearest")

            # --- Fixed Time Handling ---
            raw_time = t2m_point.time.values
            if hasattr(raw_time, "__len__") and not isinstance(raw_time, (str, bytes)):
                base_time = pd.to_datetime(raw_time[0])
            else:
                base_time = pd.to_datetime(raw_time)

            valid_times = base_time + pd.to_timedelta(t2m_point.step.values, unit="h")
            temps_c = t2m_point.values - 273.15

            # Create Series: Temperature as data, valid_times as index
            series = pd.Series(data=temps_c, index=valid_times)
            
            # Localize to Nepal Time
            if series.index.tz is None:
                series.index = series.index.tz_localize("UTC")
            series = series.tz_convert(LOCAL_TZ) # Fixed: Correctly converts series, not just index

            # Step 7: Resample to DHM standard (Ends at 08:45 AM)
            daily = series.resample(
                '1D', 
                origin='start_day', 
                offset='8h45min', 
                label='right', 
                closed='right'
            ).agg(['min', 'max'])

            daily = daily.iloc[1:7] 

            row_dict = {
                "Station": station_name,
                "District": row.get("district", "N/A"),
                "Lat": lat,
                "Long": lon,
                "DHM_Obs_Min": row.get("DHM_Min"),
                "DHM_Obs_Max": row.get("DHM_Max"),
            }

            forecast_mins = []
            for i, (date, values) in enumerate(daily.iterrows(), start=1):
                m_val = round(values["min"], 2)
                row_dict[f"Day{i}_Date"] = date.strftime("%Y-%m-%d")
                row_dict[f"Day{i}_Min"] = m_val
                row_dict[f"Day{i}_Max"] = round(values["max"], 2)
                forecast_mins.append(m_val)

            row_dict["ColdWave_Forecast_Status"] = evaluate_forecast_cold_wave(forecast_mins)
            results.append(row_dict)

        except Exception as e:
            print(f"Skipping station {row.get('station')}: {e}")

    # Step 8: Final Export
    if not results:
        print("❌ No data processed.")
        return

    final_df = pd.DataFrame(results)
    prio_map = {"Possible Severe Cold Wave": 0, "Possible Cold Wave": 1, "No Cold Wave Signal": 2}
    final_df['prio'] = final_df['ColdWave_Forecast_Status'].map(prio_map)
    final_df = final_df.sort_values('prio').drop(columns=['prio'])

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    excel_path = OUTPUT_PATH.with_suffix(".xlsx")
    final_df.to_excel(excel_path, index=False)
    
    print(f"\n✅ Success! File saved: {excel_path.resolve()}")
    print(final_df[['Station', 'Day1_Min', 'ColdWave_Forecast_Status']].head(10).to_string(index=False))

if __name__ == "__main__":
    main()
