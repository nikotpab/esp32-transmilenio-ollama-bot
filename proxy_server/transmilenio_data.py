import aiohttp
from typing import Dict, List, Optional
from datetime import datetime, timedelta

ARC_GIS_ESTACIONES_URL = (
    "https://services1.arcgis.com/HVr7PR4hP4kGFbWV/arcgis/rest/services/"
    "Estaciones_Troncales_de_TransMilenio/FeatureServer/0/query"
)

class TransmilenioDataFetcher:
    def __init__(self, cache_duration_minutes: int = 60):
        self.cache: Dict[str, any] = {}
        self.cache_timestamp: Dict[str, datetime] = {}
        self.cache_duration = timedelta(minutes=cache_duration_minutes)

    async def fetch_stations(self) -> List[Dict]:
        cache_key = "stations"
        now = datetime.now()

        if cache_key in self.cache:
            if now - self.cache_timestamp[cache_key] < self.cache_duration:
                return self.cache[cache_key]

        try:
            async with aiohttp.ClientSession() as session:
                params = {
                    "where": "1=1",
                    "outFields": "Nombre,Linea,Latitude,Longitude,Tipo",
                    "f": "json",
                    "returnGeometry": "true",
                    "outSR": "4326"
                }

                async with session.get(ARC_GIS_ESTACIONES_URL, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        features = data.get("features", [])

                        stations = []
                        for feature in features:
                            attrs = feature.get("attributes", {})
                            geometry = feature.get("geometry", {})

                            stations.append({
                                "name": attrs.get("Nombre", "Sin nombre"),
                                "line": attrs.get("Linea", "X"),
                                "type": attrs.get("Tipo", "Troncal"),
                                "lat": geometry.get("y", 0),
                                "lng": geometry.get("x", 0),
                            })

                        self.cache[cache_key] = stations
                        self.cache_timestamp[cache_key] = now

                        return stations

        except Exception as e:
            print(f"Error fetching stations: {e}")

        return self._get_fallback_stations()

    def _get_fallback_stations(self) -> List[Dict]:
        return [
            {"name": "Portal Norte", "line": "K", "type": "Troncal", "lat": 4.7089, "lng": -74.0721},
            {"name": "Calle 161", "line": "K", "type": "Troncal", "lat": 4.7021, "lng": -74.0489},
            {"name": "Calle 146", "line": "K", "type": "Troncal", "lat": 4.6912, "lng": -74.0467},
            {"name": "Calle 127", "line": "K", "type": "Troncal", "lat": 4.6834, "lng": -74.0456},
            {"name": "Calle 100", "line": "K", "type": "Troncal", "lat": 4.6656, "lng": -74.0542},
            {"name": "Calle 85", "line": "K", "type": "Troncal", "lat": 4.6589, "lng": -74.0567},
            {"name": "Calle 76", "line": "K", "type": "Troncal", "lat": 4.6534, "lng": -74.0589},
            {"name": "Calle 72", "line": "K", "type": "Troncal", "lat": 4.6489, "lng": -74.0612},
            {"name": "Calle 63", "line": "K", "type": "Troncal", "lat": 4.6401, "lng": -74.0634},
            {"name": "Calle 45", "line": "K", "type": "Troncal", "lat": 4.6234, "lng": -74.0678},
            {"name": "Calle 38", "line": "B", "type": "Troncal", "lat": 4.6156, "lng": -74.0723},
            {"name": "Calle 26", "line": "B", "type": "Troncal", "lat": 4.6089, "lng": -74.0812},
            {"name": "Calle 17", "line": "B", "type": "Troncal", "lat": 4.5978, "lng": -74.0856},
            {"name": "Calle 1", "line": "B", "type": "Troncal", "lat": 4.5889, "lng": -74.0912},
            {"name": "Portal Sur", "line": "B", "type": "Troncal", "lat": 4.5712, "lng": -74.1123},
            {"name": "Portal 80", "line": "C", "type": "Troncal", "lat": 4.6923, "lng": -74.0912},
            {"name": "Calle 80", "line": "C", "type": "Troncal", "lat": 4.6712, "lng": -74.0734},
            {"name": "Suba", "line": "C", "type": "Troncal", "lat": 4.7123, "lng": -74.0834},
            {"name": "Portal Eldorado", "line": "D", "type": "Troncal", "lat": 4.6789, "lng": -74.1234},
            {"name": "Aeropuerto", "line": "D", "type": "Troncal", "lat": 4.7012, "lng": -74.1456},
        ]

    async def find_nearest_station(
        self,
        lat: float,
        lng: float,
        radius_km: float = 1.0
    ) -> Optional[Dict]:
        stations = await self.fetch_stations()

        nearest = None
        min_distance = float('inf')

        for station in stations:
            distance = self._haversine_distance(
                lat, lng,
                station["lat"], station["lng"]
            )

            if distance < min_distance and distance <= radius_km:
                min_distance = distance
                nearest = station

        if nearest:
            nearest["distance_km"] = round(min_distance, 3)

        return nearest

    def _haversine_distance(
        self,
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float
    ) -> float:
        import math

        R = 6371

        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)

        a = (math.sin(delta_lat / 2) ** 2 +
             math.cos(lat1_rad) * math.cos(lat2_rad) *
             math.sin(delta_lon / 2) ** 2)

        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c

transmilenio_fetcher = TransmilenioDataFetcher()

if __name__ == "__main__":
    import asyncio

    async def test():
        fetcher = TransmilenioDataFetcher()
        stations = await fetcher.fetch_stations()

        print(f"Total estaciones: {len(stations)}")
        print("\nPrimeras 5 estaciones:")
        for station in stations[:5]:
            print(f"  - {station['name']} (Linea {station['line']})")

    asyncio.run(test())
