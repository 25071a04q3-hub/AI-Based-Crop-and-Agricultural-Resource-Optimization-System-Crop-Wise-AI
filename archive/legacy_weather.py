import requests

def fetch_weather_forecast(lat: float, lon: float) -> dict:
    """
    Fetches real-time/forecast weather data from free Open-Meteo API.
    Falls back gracefully to seasonal defaults on network error or invalid coordinates.
    """
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,rain&daily=rain_sum&timezone=auto"
    try:
        response = requests.get(url, timeout=4)
        if response.status_code == 200:
            data = response.json()
            curr = data.get("current", {})
            daily = data.get("daily", {})
            rain_sum = sum(daily.get("rain_sum", [10.0])) if daily.get("rain_sum") else 50.0
            
            return {
                "temperature": float(curr.get("temperature_2m", 26.5)),
                "humidity": float(curr.get("relative_humidity_2m", 65.0)),
                "rainfall": float(rain_sum * 10.0), # Approximate seasonal multiplier
                "source": "Open-Meteo Live API"
            }
    except Exception:
        pass

    # Fallback seasonal defaults for India
    return {
        "temperature": 27.5,
        "humidity": 65.0,
        "rainfall": 120.0,
        "source": "Fallback Defaults (Offline / Weather API Unavailable)"
    }
