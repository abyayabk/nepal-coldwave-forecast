from pathlib import Path
from datetime import datetime, timezone
from ecmwf.opendata import Client
from src.config import GRIB_PATH

def fetch_forecast(steps=None, date=None):
    """
    Downloads ECMWF 2m temperature forecast (GRIB).
    Defaults to the latest available forecast run if date is None.
    """
    # 144 hours = 6 days of forecast
    if steps is None:
        steps = list(range(0, 145, 3))

    client = Client(source="aws")

    # Format parameters for the request
    params = {
        "type": "fc",
        "step": steps,
        "param": "2t",
        "target": str(GRIB_PATH)
    }

    # If date is provided, format it; otherwise ECMWF fetches 'latest'
    if date:
        if isinstance(date, str):
            date_obj = datetime.strptime(date, "%Y-%m-%d")
        else:
            date_obj = date
        params["date"] = date_obj.strftime("%Y%m%d")

    # Ensure target directory exists
    GRIB_PATH.parent.mkdir(parents=True, exist_ok=True)

    print(f"Requesting forecast data from ECMWF (AWS)...")
    try:
        client.retrieve(**params)
        print(f"✅ Success: Saved to {GRIB_PATH}")
    except Exception as e:
        print(f"❌ Error fetching forecast: {e}")