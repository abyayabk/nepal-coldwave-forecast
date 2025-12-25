# src/api/dhm_scraper.py
from selenium import webdriver
import chromedriver_autoinstaller
import pandas as pd
import json
import math

def fetch_dhm_temperature(url: str = "https://dhm.gov.np/hydrology/surface-observation") -> pd.DataFrame:
    """
    Scrape the DHM website and return temperature data as a DataFrame.
    Match stations by lat/lon within a small tolerance.
    """
    # Load JSON stations
    with open("data/stations.json") as f:
        stations = json.load(f)

    # Ensure correct ChromeDriver
    chromedriver_autoinstaller.install()

    # Selenium options
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")

    driver = webdriver.Chrome(options=options)
    driver.get(url)

    # Get JS global variable
    temp_data = driver.execute_script("return temperature;")
    driver.quit()

    # Prepare result
    results = []

    tolerance = 0.01  # ~1 km difference allowed

    for station in stations:
        lat = station["lat"]
        lon = station["lon"]
        matched = False

        for dhm in temp_data:
            dhm_lat = dhm.get("latitude")
            dhm_lon = dhm.get("longitude")

            if math.isclose(dhm_lat, lat, abs_tol=tolerance) and math.isclose(dhm_lon, lon, abs_tol=tolerance):
                obs = dhm.get("observations", [])

                # Initialize min and max
                min_temp = None
                max_temp = None

                for o in obs:
                    if "data" not in o or not isinstance(o["data"], list):
                        continue

                    if o.get("parameter_code") == "TX_1D":  # daily max
                        values = [
                            d.get("value") for d in o["data"]
                            if isinstance(d, dict) and d.get("value") is not None
                        ]
                        if values:
                            max_temp = max(values)

                    elif o.get("parameter_code") == "TN_1D":  # daily min
                        values = [
                            d.get("value") for d in o["data"]
                            if isinstance(d, dict) and d.get("value") is not None
                        ]
                        if values:
                            min_temp = min(values)


                results.append({
                    "station": station["station"],
                    "lat": lat,
                    "lon": lon,
                    "t_min": min_temp,
                    "t_max": max_temp
                })
                matched = True
                break  # stop after first match

    final_df = pd.DataFrame(results)
    return final_df
