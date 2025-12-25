# src/run.py
import numpy as np
import pandas as pd
import xarray as xr
import json
from datetime import datetime
from src.api.dhm_scraper import fetch_dhm_temperature
from src.api.ecmwf_fetch import fetch_forecast
from src.config import (
    OUTPUT_PATH,
    GRIB_PATH,
    LOCAL_TZ
)

# Step 1: Load station metadata from a local JSON file
print("Loading stations from JSON...")
with open("data/stations.json") as f:
    stations_data = json.load(f)

# Convert JSON data to a pandas DataFrame for easier handling
stations_df = pd.DataFrame(stations_data)

# Step 2: Fetch the ECMWF forecast GRIB file
print("Fetching ECMFW api data...")
# Downloads forecast data to GRIB_PATH
# 🛑🛑🛑🛑🛑🛑 COMMENT OUT ME TO FETCH ECMFW API DATA 🛑🛑🛑🛑🛑🛑
fetch_forecast()  

# Step 3: Fetch observed temperature data from DHM website
print("Fetching DHM observed station data...")
dhm_df = fetch_dhm_temperature()  # Returns a DataFrame with t_min, t_max, lat, lon for stations

# Step 4: Merge station metadata with DHM observed data based on 'station' name
df = pd.merge(
    stations_df,
    dhm_df.rename(columns={"lat": "dhm_lat", "lon": "dhm_lon", "t_min": "DHM_Min", "t_max": "DHM_Max"}),
    how="left",
    on="station"
)

# Step 5: Open the ECMWF GRIB file using xarray + cfgrib backend
print("Opening ECMWF GRIB...")
ds = xr.open_dataset(GRIB_PATH, engine="cfgrib")
# Select the 2m temperature variable (t2m or 2t)
var_name = "t2m" if "t2m" in ds else "2t"
t2m = ds[var_name]

# Step 6: Initialize a list to store processed station results
results = []

# Step 7: Loop through each station row in the merged DataFrame
for _, row in df.iterrows():
    station_name = row["station"]
    lat = float(row["lat"])       # Station latitude from JSON
    lon = float(row["lon"])       # Station longitude from JSON
    dhm_min = row.get("DHM_Min")  # Observed min temp
    dhm_max = row.get("DHM_Max")  # Observed max temp

    # Step 8: Select the nearest ECMWF grid point for this station
    try:
        t2m_point = t2m.sel(latitude=lat, longitude=lon % 360, method="nearest")
    except KeyError:
        t2m_point = t2m.sel(lat=lat, lon=lon % 360, method="nearest")

    # Step 9: Build the forecast time series for this station
    base_time = t2m_point.time.values  # GRIB file reference time
    if base_time.ndim > 0:
        base_time = base_time[0]  # Take first element if array
    # Add forecast step hours to base_time to get actual valid times
    valid_times = pd.to_datetime(base_time) + pd.to_timedelta(t2m_point.step.values, unit="h")

    # Convert temperatures from Kelvin to Celsius
    temps_c = t2m_point.values - 273.15
    series = pd.Series(temps_c, index=valid_times)
    # Convert timezone to local timezone
    series.index = series.index.tz_localize("UTC").tz_convert(LOCAL_TZ)

    # Step 10: Aggregate 6-hourly forecast into daily min/max, select first 10 days
    daily = series.resample("1D").agg(["min", "max"]).iloc[:10]

    # Step 11: Build a dictionary to store all data for this station
    row_dict = {
        "Station": station_name,
        "Long": lon,
        "Lat": lat,
        "p1": row.get("p1"),
        "p5": row.get("p5"),
        "p10": row.get("p10"),
        "mean": row.get("mean"),
        "DHM_Min": dhm_min,
        "DHM_Max": dhm_max
    }

    # Step 12: Add all 10 forecast days (date, min, max) to the dictionary
    for i, (date, values) in enumerate(daily.iterrows(), start=1):
        row_dict[f"Day{i}_Date"] = date.strftime("%Y-%m-%d")
        row_dict[f"Day{i}_Min"] = round(values["min"], 2)
        row_dict[f"Day{i}_Max"] = round(values["max"], 2)

    # Step 13: Append the station dictionary to the results list
    results.append(row_dict)

# Step 14: Convert the results list into a final DataFrame
final_df = pd.DataFrame(results)

# Step 15: Save the final DataFrame to CSV at OUTPUT_PATH
# final_df.to_csv(OUTPUT_PATH, index=False)
# print(f"Data saved to {OUTPUT_PATH}")

# Also save to Excel
excel_path = OUTPUT_PATH.with_suffix(".xlsx")  # same path, but .xlsx extension
final_df.to_excel(excel_path, index=False)
print(f"Data saved to Excel at {excel_path}")