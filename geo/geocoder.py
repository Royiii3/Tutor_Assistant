import requests
from typing import Optional


class Geocoder:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.api_url = "https://restapi.amap.com/v3/geocode/geo"

    def geocode(self, address: str) -> Optional[tuple[float, float]]:
        if not address:
            return None

        try:
            response = requests.get(
                self.api_url,
                params={"key": self.api_key, "address": address, "city": "杭州"},
                timeout=10
            )
            data = response.json()
            if data.get("status") == "1" and data.get("geocodes"):
                location = data["geocodes"][0]["location"]
                lng, lat = location.split(",")
                return (float(lng), float(lat))
            return None
        except Exception:
            return None
