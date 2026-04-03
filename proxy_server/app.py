import os
import json
import asyncio
import aiohttp
from datetime import datetime
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

load_dotenv()

app = FastAPI(title="TransMilenio/SITP Route Bot Proxy")

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")
TRANSMILENIO_API_URL = os.getenv("TRANSMILENIO_API_URL", "")
MOOVIT_BASE_URL = os.getenv("MOOVIT_BASE_URL", "https://moovitapp.com")

@dataclass
class RouteRequest:
    message: str
    chat_id: str
    timestamp: str
    location: str = "Bogota, Colombia"

class RouteResponse(BaseModel):
    route_summary: str
    steps: List[str]
    estimated_time: str
    distance: str
    cost: str
    recommendations: str
    alternatives: List[str]
    raw_entities: Optional[Dict] = None

class TelegramRequest(BaseModel):
    message: str
    chat_id: str
    timestamp: Optional[str] = None
    location: Optional[str] = "Bogota, Colombia"

ESTACIONES_TRONCALES = {
    "portal norte": {"lat": 4.7089, "lng": -74.0721, "line": "K"},
    "calle 161": {"lat": 4.7021, "lng": -74.0489, "line": "K"},
    "calle 146": {"lat": 4.6912, "lng": -74.0467, "line": "K"},
    "calle 127": {"lat": 4.6834, "lng": -74.0456, "line": "K"},
    "calle 100": {"lat": 4.6656, "lng": -74.0542, "line": "K"},
    "calle 85": {"lat": 4.6589, "lng": -74.0567, "line": "K"},
    "calle 76": {"lat": 4.6534, "lng": -74.0589, "line": "K"},
    "calle 72": {"lat": 4.6489, "lng": -74.0612, "line": "K"},
    "calle 63": {"lat": 4.6401, "lng": -74.0634, "line": "K"},
    "calle 45": {"lat": 4.6234, "lng": -74.0678, "line": "K"},
    "calle 38": {"lat": 4.6156, "lng": -74.0723, "line": "B"},
    "calle 26": {"lat": 4.6089, "lng": -74.0812, "line": "B"},
    "calle 17": {"lat": 4.5978, "lng": -74.0856, "line": "B"},
    "calle 1": {"lat": 4.5889, "lng": -74.0912, "line": "B"},
    "portal sur": {"lat": 4.5712, "lng": -74.1123, "line": "B"},
    "portal 80": {"lat": 4.6923, "lng": -74.0912, "line": "C"},
    "calle 80": {"lat": 4.6712, "lng": -74.0734, "line": "C"},
    "suba": {"lat": 4.7123, "lng": -74.0834, "line": "C"},
    "portal eldorado": {"lat": 4.6789, "lng": -74.1234, "line": "D"},
    "aeropuerto": {"lat": 4.7012, "lng": -74.1456, "line": "D"},
    "guatoque": {"lat": 4.5834, "lng": -74.0934, "line": "B"},
    "general santander": {"lat": 4.5756, "lng": -74.0989, "line": "B"},
    "centro": {"lat": 4.6045, "lng": -74.0756, "line": "B"},
    "las aguas": {"lat": 4.5989, "lng": -74.0812, "line": "B"},
}

TARIFA_TRANSMILENIO = 2950
TARIFA_SITP = 2600
TARIFA_INTEGRAL = 3950

async def extract_entities_with_ollama(message: str) -> Dict[str, Any]:
    prompt = f"""
Eres un asistente experto en transporte publico de Bogota.
Extrae las entidades de la siguiente solicitud del usuario.

Solicitud: "{message}"

Devuelve SOLO un JSON valido con este formato:
{{
    "origin": "lugar de origen (puede ser direccion, estacion, o punto de referencia)",
    "destination": "lugar de destino",
    "time": "hora especifica o 'now' si es inmediato",
    "date": "fecha especifica o 'today'",
    "preferences": ["rapido", "economico", "pocas_transmilenio", etc] o null
}}

Si no puedes identificar alguna entidad, usa null para ese campo.
"""

    try:
        async with aiohttp.ClientSession() as session:
            payload = {
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "num_predict": 500
                }
            }

            async with session.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    text = result.get("response", "")

                    start_idx = text.find("{")
                    end_idx = text.rfind("}") + 1

                    if start_idx >= 0 and end_idx > start_idx:
                        json_str = text[start_idx:end_idx]
                        return json.loads(json_str)

    except Exception as e:
        print(f"Error calling Ollama: {e}")

    return extract_entities_fallback(message)

def extract_entities_fallback(message: str) -> Dict[str, Any]:
    message_lower = message.lower()

    origin = None
    destination = None

    for station in ESTACIONES_TRONCALES.keys():
        if station in message_lower:
            if origin is None:
                origin = station
            elif destination is None:
                destination = station
                break

    time = "now"
    if "manana" in message_lower or "manana" in message_lower:
        time = "morning"
    elif "tarde" in message_lower:
        time = "afternoon"
    elif "noche" in message_lower:
        time = "night"

    return {
        "origin": origin,
        "destination": destination,
        "time": time,
        "date": "today",
        "preferences": None
    }

async def get_distance_and_time(
    origin: str,
    destination: str,
    departure_time: str = "now"
) -> Dict[str, Any]:
    if not GOOGLE_MAPS_API_KEY:
        return {
            "distance_km": 5.0,
            "duration_min": 25,
            "error": "Google Maps API key not configured"
        }

    try:
        async with aiohttp.ClientSession() as session:
            url = "https://maps.googleapis.com/maps/api/directions/json"
            params = {
                "origin": origin + ", Bogota, Colombia",
                "destination": destination + ", Bogota, Colombia",
                "mode": "transit",
                "departure_time": departure_time,
                "key": GOOGLE_MAPS_API_KEY,
                "language": "es"
            }

            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()

                    if data.get("status") == "OK" and data.get("routes"):
                        route = data["routes"][0]
                        leg = route["legs"][0]

                        return {
                            "distance_km": leg["distance"]["value"] / 1000,
                            "duration_min": leg["duration"]["value"] / 60,
                            "steps": leg.get("steps", []),
                            "transit_details": extract_transit_details(leg["steps"])
                        }

    except Exception as e:
        print(f"Error calling Google Maps: {e}")

    return {
        "distance_km": 5.0,
        "duration_min": 25,
        "error": "Could not fetch from Google Maps"
    }

def extract_transit_details(steps: List[Dict]) -> List[Dict]:
    transit_info = []

    for step in steps:
        if "transit_details" in step:
            transit = step["transit_details"]
            transit_info.append({
                "line": transit.get("line", {}).get("name", ""),
                "type": transit.get("line", {}).get("vehicle", {}).get("type", ""),
                "departure_stop": transit.get("departure_stop", {}).get("name", ""),
                "arrival_stop": transit.get("arrival_stop", {}).get("name", ""),
            })

    return transit_info

def calculate_optimal_route(
    origin: str,
    destination: str,
    google_maps_data: Dict,
    time_of_day: str
) -> Dict[str, Any]:
    origin_lower = origin.lower() if origin else ""
    dest_lower = destination.lower() if destination else ""

    origin_is_troncal = any(s in origin_lower for s in ESTACIONES_TRONCALES.keys())
    dest_is_troncal = any(s in dest_lower for s in ESTACIONES_TRONCALES.keys())

    if origin_is_troncal and dest_is_troncal:
        route_type = "troncal"
        base_fare = TARIFA_TRANSMILENIO
    elif origin_is_troncal or dest_is_troncal:
        route_type = "integral"
        base_fare = TARIFA_INTEGRAL
    else:
        route_type = "sitp"
        base_fare = TARIFA_SITP

    distance_km = google_maps_data.get("distance_km", 5.0)
    duration_min = google_maps_data.get("duration_min", 25)

    traffic_factor = 1.0
    if time_of_day in ["morning", "afternoon"]:
        traffic_factor = 1.3
        duration_min *= traffic_factor

    steps = generate_route_steps(origin, destination, route_type, google_maps_data)
    lines = determine_lines(origin_lower, dest_lower)

    return {
        "route_type": route_type,
        "steps": steps,
        "estimated_time": f"{int(duration_min)} minutos",
        "distance": f"{distance_km:.1f} km",
        "cost": f"${base_fare:,.0f} COP",
        "lines": lines,
        "traffic_factor": traffic_factor
    }

def generate_route_steps(
    origin: str,
    destination: str,
    route_type: str,
    google_maps_data: Dict
) -> List[str]:
    steps = []

    if route_type == "troncal":
        steps.append(f"Camina hacia la estacion mas cercana a {origin}")
        steps.append("Valida tu tarjeta en el torniquete")
        steps.append("Sube al bus en la plataforma (verifica la direccion)")
        steps.append(f"Baja en la estacion cercana a {destination}")
        steps.append("Camina hacia tu destino final")

    elif route_type == "integral":
        steps.append(f"Camina hacia {origin}")
        if any(s in origin.lower() for s in ESTACIONES_TRONCALES.keys()):
            steps.append("Toma Transmilenio hasta la estacion de conexion")
            steps.append("Haz transbordo a bus SITP (misma tarjeta)")
        else:
            steps.append("Toma bus SITP hacia estacion Transmilenio")
            steps.append("Transborda a Transmilenio")
        steps.append(f"Dirigete a {destination}")
        steps.append("Camina hacia tu destino final")

    else:
        steps.append(f"Camina hacia el paradero mas cercano a {origin}")
        steps.append("Sube al bus SITP (paga al subir)")
        steps.append(f"Baja en el paradero cercano a {destination}")
        steps.append("Camina hacia tu destino final")

    return steps

def determine_lines(origin: str, destination: str) -> List[str]:
    lines = []

    for station_name, station_data in ESTACIONES_TRONCALES.items():
        if station_name in origin:
            line = station_data["line"]
            if line not in lines:
                lines.append(line)
        if station_name in destination:
            line = station_data["line"]
            if line not in lines:
                lines.append(line)

    return lines if lines else ["SITP"]

async def get_bus_frequency(station: str, line: str) -> Dict[str, Any]:
    frequencies = {
        "K": {"morning": 3, "afternoon": 4, "night": 8, "default": 5},
        "B": {"morning": 4, "afternoon": 5, "night": 10, "default": 6},
        "C": {"morning": 5, "afternoon": 6, "night": 12, "default": 7},
        "D": {"morning": 6, "afternoon": 7, "night": 15, "default": 8},
        "SITP": {"morning": 8, "afternoon": 10, "night": 20, "default": 12},
    }

    time_of_day = "default"
    now = datetime.now()
    hour = now.hour

    if 6 <= hour < 9:
        time_of_day = "morning"
    elif 17 <= hour < 20:
        time_of_day = "afternoon"
    elif 20 <= hour or hour < 6:
        time_of_day = "night"

    line_key = line.upper() if line in ["K", "B", "C", "D"] else "SITP"
    freq_data = frequencies.get(line_key, frequencies["SITP"])
    frequency_min = freq_data.get(time_of_day, freq_data["default"])

    return {
        "frequency_minutes": frequency_min,
        "next_bus": f"en {frequency_min} min",
        "line": line
    }

@app.post("/api/route", response_model=RouteResponse)
async def calculate_route(request: TelegramRequest):
    entities = await extract_entities_with_ollama(request.message)

    origin = entities.get("origin")
    destination = entities.get("destination")
    time = entities.get("time", "now")
    preferences = entities.get("preferences")

    if not origin or not destination:
        return RouteResponse(
            route_summary="No pude identificar origen y destino",
            steps=["Por favor, especifica claramente tu punto de origen y destino"],
            estimated_time="-",
            distance="-",
            cost="-",
            recommendations="Ejemplo: 'De Calle 100 a Portal Norte'",
            alternatives=[],
            raw_entities=entities
        )

    maps_data = await get_distance_and_time(origin, destination, time)

    route_data = calculate_optimal_route(
        origin=origin,
        destination=destination,
        google_maps_data=maps_data,
        time_of_day=time
    )

    lines = route_data.get("lines", [])
    frequency_info = await get_bus_frequency(origin, lines[0] if lines else "SITP")

    route_summary = f"Ruta: {origin} -> {destination}\n"
    route_summary += f"Tipo: {route_data['route_type'].upper()}\n"
    route_summary += f"Frecuencia: cada {frequency_info['frequency_minutes']} min"

    recommendations = generate_recommendations(
        route_data["route_type"],
        route_data["cost"],
        time,
        preferences
    )

    alternatives = generate_alternatives(origin, destination)

    return RouteResponse(
        route_summary=route_summary,
        steps=route_data["steps"],
        estimated_time=route_data["estimated_time"],
        distance=route_data["distance"],
        cost=route_data["cost"],
        recommendations=recommendations,
        alternatives=alternatives,
        raw_entities=entities
    )

@app.get("/api/status")
async def get_status():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "ollama_url": OLLAMA_BASE_URL,
        "model": OLLAMA_MODEL,
        "google_maps_configured": bool(GOOGLE_MAPS_API_KEY)
    }

@app.get("/api/stations")
async def get_stations():
    return {
        "stations": [
            {"name": name, "line": data["line"], "lat": data["lat"], "lng": data["lng"]}
            for name, data in ESTACIONES_TRONCALES.items()
        ]
    }

def generate_recommendations(
    route_type: str,
    cost: str,
    time: str,
    preferences: Optional[List[str]]
) -> str:
    recs = []

    if route_type == "troncal":
        recs.append("Usa plataforma correcta (verifica direccion del bus)")
    elif route_type == "integral":
        recs.append("Tienes 1 hora para transbordo gratuito")
    else:
        recs.append("Paga al subir al bus")

    if time in ["morning", "afternoon"]:
        recs.append("Hora pico: espera mayor congestion")

    if preferences:
        if "rapido" in preferences:
            recs.append("Ruta optimizada por tiempo")
        if "economico" in preferences:
            recs.append("Ruta optimizada por costo")

    return " | ".join(recs)

def generate_alternatives(origin: str, destination: str) -> List[str]:
    return [
        f"Ruta directa SITP (~15-20 min mas)",
        f"Taxi/Uber: ~$15000-25000 COP, 15-20 min",
        f"Bicicleta: usa ciclorruta si esta disponible"
    ]

if __name__ == "__main__":
    import uvicorn

    print("=" * 60)
    print("PROXY SERVER - BOT TELEGRAM TRANSMILENIO/SITP")
    print("=" * 60)
    print(f"Ollama URL: {OLLAMA_BASE_URL}")
    print(f"Model: {OLLAMA_MODEL}")
    print(f"Google Maps: {'Configurado' if GOOGLE_MAPS_API_KEY else 'No configurado'}")
    print("=" * 60)

    uvicorn.run(app, host="0.0.0.0", port=5000)
