import requests
from typing import Optional


class DistanceCalculator:
    MODE_MAP = {
        "电动自行车": "riding",
        "骑行": "riding",
        "驾车": "driving",
        "步行": "walking",
        "公交": "transit"
    }

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://restapi.amap.com/v3/direction"

    def calculate(
        self,
        origin: Optional[tuple[float, float]],
        destination: Optional[tuple[float, float]],
        mode: str = "riding"
    ) -> Optional[dict]:
        if not origin or not destination:
            return None

        mode = self.MODE_MAP.get(mode, "riding")
        url = f"{self.base_url}/{mode}"

        try:
            response = requests.get(
                url,
                params={
                    "key": self.api_key,
                    "origin": f"{origin[0]},{origin[1]}",
                    "destination": f"{destination[0]},{destination[1]}"
                },
                timeout=10
            )
            data = response.json()
            if data.get("status") == "1":
                path = data["route"]["paths"][0]
                return {
                    "duration": int(path["duration"]) // 60,
                    "distance": int(path["distance"]) / 1000
                }
            return None
        except Exception:
            return None
