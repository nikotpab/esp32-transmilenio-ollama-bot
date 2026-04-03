import os
import json
import asyncio
import aiohttp
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Optional, Dict, List, Any
from dotenv import load_dotenv

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")

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

BLOCKED_STATIONS = {}
VAGONES_COMPLEJOS = {
    "ricaurte": {
        "g43": "Vagón 2 (Túnel paralela NQS)",
        "b12": "Vagón 1 (NQS Norte)",
        "j23": "Vagón 3 (Calle 13)"
    },
    "calle 100": {
        "8": "Vagón 3",
        "b10": "Vagón 1",
        "g12": "Vagón 2"
    },
    "heroes": {
        "8": "Vagón 1",
        "g11": "Vagón 2"
    }
}
WEATHER_CACHE = {"is_raining": False, "last_check": 0}
NEWS_BLOCK_CACHE = {"stations": {}, "last_check": 0}

async def update_live_news_blocks():
    now = time.time()
    if now - NEWS_BLOCK_CACHE["last_check"] > 600:
        NEWS_BLOCK_CACHE["last_check"] = now
        try:
            url = "https://news.google.com/rss/search?q=Transmilenio+bloqueo+OR+desv%C3%ADo+OR+cierre+when:1d&hl=es-419&gl=CO&ceid=CO:es-419"
            async with aiohttp.ClientSession() as s:
                async with s.get(url, timeout=10) as r:
                    if r.status == 200:
                        xml_data = await r.text()
                        root = ET.fromstring(xml_data)
                        news_stations = {}
                        
                        for item in root.findall(".//item"):
                            title = item.find("title")
                            if title is not None and title.text:
                                title_lower = title.text.lower()
                                if any(kw in title_lower for kw in ["bloqueo", "bloqueos", "cierre", "cerrada", "desvío", "desvio", "obras"]):
                                    for st_name in ESTACIONES_TRONCALES.keys():
                                        if st_name in title_lower:
                                            news_stations[st_name] = now + 7200
                        NEWS_BLOCK_CACHE["stations"] = news_stations
        except Exception as e:
            print(f"News check error: {e}")

async def check_weather() -> bool:
    now = time.time()
    if now - WEATHER_CACHE["last_check"] > 900:  
        WEATHER_CACHE["last_check"] = now
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get("https://api.open-meteo.com/v1/forecast?latitude=4.6&longitude=-74.08&current=precipitation", timeout=5) as r:
                    if r.status == 200:
                        data = await r.json()
                        precip = data.get("current", {}).get("precipitation", 0)
                        WEATHER_CACHE["is_raining"] = precip > 0
        except Exception as e:
            print(f"Weather error: {e}")
            WEATHER_CACHE["is_raining"] = False
    return WEATHER_CACHE["is_raining"]

def is_night_time():
    from datetime import datetime
    utc_hour = datetime.utcnow().hour
    bogota_hour = (utc_hour - 5) % 24
    return bogota_hour >= 21 or bogota_hour < 5

def parse_departure_time(term: str) -> str:
    if term == "now": return "now"
    from datetime import datetime, timedelta
    now = datetime.utcnow() - timedelta(hours=5)
    target = now
    if term == "morning":
        target = now.replace(hour=7, minute=0, second=0, microsecond=0)
        if now.hour >= 7: target += timedelta(days=1)
    elif term == "afternoon":
        target = now.replace(hour=14, minute=0, second=0, microsecond=0)
        if now.hour >= 14: target += timedelta(days=1)
    elif term == "night":
        target = now.replace(hour=19, minute=0, second=0, microsecond=0)
        if now.hour >= 19: target += timedelta(days=1)
    else: return "now"
    target_utc = target + timedelta(hours=5)
    return str(int(target_utc.timestamp()))

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
    if "manana" in message_lower:
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

async def get_distance_and_time(origin: str, destination: str, departure_time: str = "now") -> List[Dict[str, Any]]:
    if not GOOGLE_MAPS_API_KEY:
        return [{"distance_km": 5.0, "duration_min": 25, "error": "Google Maps API key not configured"}]
    try:
        async with aiohttp.ClientSession() as session:
            url = "https://maps.googleapis.com/maps/api/directions/json"
            def format_place(place: str) -> str:
                lower = place.lower()
                is_troncal = any(st in lower for st in ESTACIONES_TRONCALES.keys())
                if is_troncal:
                    if "estacion" not in lower and "estación" not in lower and "portal" not in lower:
                        return f"Estación de Transmilenio {place}, Bogota, Colombia"
                    else:
                        # Ensure it says Estación de Transmilenio for better accuracy
                        return f"{place}, Bogota, Colombia".replace("estacion ", "Estación de Transmilenio ").replace("estación ", "Estación de Transmilenio ")
                return f"{place}, Bogota, Colombia"
                
            is_station_origin = any(st in origin.lower() for st in ESTACIONES_TRONCALES.keys()) or "estacion" in origin.lower() or "estación" in origin.lower() or "portal" in origin.lower()

            is_rain = await check_weather()
            is_night = is_night_time()
            
            await update_live_news_blocks()

            current_t = time.time()
            expired = [k for k, v in BLOCKED_STATIONS.items() if v < current_t]
            for k in expired: del BLOCKED_STATIONS[k]
            
            active_blocks = set(BLOCKED_STATIONS.keys())
            news_blocks = NEWS_BLOCK_CACHE["stations"]
            for k, v in news_blocks.items():
                if v > current_t:
                    active_blocks.add(k)

            params = {
                "origin": format_place(origin),
                "destination": format_place(destination),
                "mode": "transit",
                "alternatives": "true",
                "departure_time": parse_departure_time(departure_time),
                "key": GOOGLE_MAPS_API_KEY,
                "language": "es"
            }
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("status") == "OK" and data.get("routes"):
                        routes_data = data["routes"]
                        
                        valid_routes = []
                        for r in routes_data:
                            blocked = False
                            for step in r["legs"][0].get("steps", []):
                                if step.get("travel_mode") == "TRANSIT":
                                    td = step.get("transit_details", {})
                                    d_name = td.get("departure_stop", {}).get("name", "").lower()
                                    a_name = td.get("arrival_stop", {}).get("name", "").lower()
                                    for b_station in active_blocks:
                                        if b_station in d_name or b_station in a_name:
                                            blocked = True
                                            break
                                if blocked: break
                            if not blocked:
                                valid_routes.append(r)
                                
                        if not valid_routes:
                            if active_blocks:
                                return [{"error": "distancia", "route_summary": "🚶‍♀️ **Sin rutas encontradas (Posibles Bloqueos)**", "steps": ["No logramos encontrar ruta. Seguramente las vías alternas no rinden fruto porque hay estaciones bloqueadas.", "Intenta buscar una estación más lejana."]}]
                            return [{"error": "distancia", "route_summary": "🚶‍♀️ **Sin rutas encontradas**", "steps": ["No logramos encontrar opciones de transporte público entre estos dos puntos.", "Intenta especificar mejor un cruce, calle u otra estación cercana."]}]

                        if len(valid_routes) > 1:
                            def route_cost(route):
                                duration = route["legs"][0].get("duration", {}).get("value", 999999)
                                
                                walk_dist = 0
                                sitp_steps = 0
                                for step in route["legs"][0].get("steps", []):
                                    if step.get("travel_mode") == "WALKING":
                                        walk_dist += step.get("distance", {}).get("value", 0)
                                    if step.get("travel_mode") == "TRANSIT":
                                        agencies = step.get("transit_details", {}).get("line", {}).get("agencies", [])
                                        agency_names = [a.get("name", "").upper() for a in agencies]
                                        if not any("TRONCAL" in name or "DUAL" in name for name in agency_names):
                                            sitp_steps += 1
                                            
                                if is_station_origin:
                                    duration += sitp_steps * 1000000
                                elif is_night:
                                    duration += sitp_steps * 500000
                                    
                                if is_rain and walk_dist > 400:
                                    duration += 200000
                                    
                                return duration
                            
                            valid_routes.sort(key=route_cost)
                        
                        top_routes = []
                        for route in valid_routes[:1]:
                            leg = route["legs"][0]
                            top_routes.append({
                                "distance_km": leg["distance"]["value"] / 1000,
                                "duration_min": leg["duration"]["value"] / 60,
                                "steps": leg.get("steps", []),
                                "transit_details": extract_transit_details(leg["steps"])
                            })
                        return top_routes
    except Exception as e:
        print(f"Error calling Google Maps: {e}")
    return [{"distance_km": 5.0, "duration_min": 25, "error": "Could not fetch from Google Maps"}]

def extract_transit_details(steps: List[Dict]) -> List[Dict]:
    transit_info = []
    for step in steps:
        if "transit_details" in step:
            transit = step["transit_details"]
            line_data = transit.get("line", {})
            line_name = line_data.get("short_name") or line_data.get("name") or "bus"
            
            dep_time_val = transit.get("departure_time", {}).get("value")
            
            transit_info.append({
                "line": line_name,
                "type": line_data.get("vehicle", {}).get("type", ""),
                "departure_stop": transit.get("departure_stop", {}).get("name", ""),
                "arrival_stop": transit.get("arrival_stop", {}).get("name", ""),
                "departure_time_unix": dep_time_val
            })
    return transit_info

def generate_route_steps(origin: str, destination: str, route_type: str, google_maps_data: Dict) -> List[str]:
    steps = []
    transit_info = google_maps_data.get("transit_details", [])
    
    if transit_info:
        for i, t in enumerate(transit_info):
            line_name = t.get('line', 'bus')
            dep_stop = t.get('departure_stop', origin)
            arr_stop = t.get('arrival_stop', destination)
            
            vagon_info = ""
            for st, lines in VAGONES_COMPLEJOS.items():
                if st in dep_stop.lower():
                    for ln, v in lines.items():
                        if ln == line_name.lower():
                            vagon_info = f" ({v})"
                            break
                    break
            
            if len(transit_info) == 1:
                steps.append(f"📍 **Sube en:** {dep_stop}")
                steps.append(f"🚌 **Toma el bus:** {line_name}{vagon_info}")
                steps.append(f"📍 **Baja en:** {arr_stop}")
            else:
                if i == 0:
                    steps.append(f"📍 **Sube en:** {dep_stop}")
                    steps.append(f"🚌 **Toma el bus:** {line_name}{vagon_info} hasta {arr_stop}")
                else:
                    steps.append(f"🔄 **Bájate allí y haz transbordo al bus:** {line_name}{vagon_info}")
                    if i == len(transit_info) - 1:
                        steps.append(f"📍 **Baja finalmente en:** {arr_stop}")
                    else:
                        steps.append(f"📍 **Baja en:** {arr_stop}")
    else:
        steps.append(f"📍 **Sube en:** el paradero más cercano a {origin}")
        steps.append(f"🚌 **Toma el bus:** de la ruta que te lleve hacia {destination}")
        steps.append(f"📍 **Baja en:** la cercanía de {destination}")

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

def calculate_optimal_route(origin: str, destination: str, google_maps_data: Dict, time_of_day: str) -> Dict[str, Any]:
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



def format_route_response(doc: Dict[str, Any]) -> str:
    if "options" not in doc:
        formatted = f"{doc.get('route_summary', '')}\n"
        for step in doc.get("steps", []):
            formatted += f"{step}\n"
        return formatted

    formatted = f"*Ruta Recomendada*\n"
    formatted += f"{doc.get('header', '')}\n\n"
    
    for option in doc["options"][:1]:
        if "route_summary" in option:
            formatted += option["route_summary"] + "\n\n"
        if "steps" in option:
            for step in option["steps"]:
                formatted += f"{step}\n"
            formatted += "\n"
        
        time_dist = []
        if "estimated_time" in option:
            time_dist.append(f"Tiempo: {option['estimated_time']}")
        if "distance" in option:
            time_dist.append(f"Distancia: {option['distance']}")
        if time_dist:
            formatted += " | ".join(time_dist) + "\n\n"
            
    return formatted.strip()

# --- TELEGRAM BOT HANDLERS ---

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome = (
        "*Bot de Transporte Bogota*\n\n"
        "Te ayudo a encontrar la mejor ruta usando Transmilenio y SITP.\n\n"
        "*Comandos disponibles:*\n"
        "/start - Mostrar este mensaje\n"
        "/status - Estado del sistema\n"
        "/routes - Estaciones principales\n\n"
        "*Como usar:*\n"
        "Simplemente escribe tu ruta:\n"
        "```\n"
        "De Calle 100 a Portal Norte\n"
        "De Mi casa al Centro a las 8am\n"
        "```\n"
        "El bot entendera tu solicitud y te dara la mejor ruta."
    )
    await update.message.reply_text(welcome, parse_mode="Markdown")

async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status = (
        "*Estado del Sistema:*\n\n"
        f"Docker/Bot: Corriendo\n"
        f"Ollama URL: {OLLAMA_BASE_URL}\n"
        f"Modelo: {OLLAMA_MODEL}\n"
        f"Google Maps: {'Configurado' if GOOGLE_MAPS_API_KEY else 'No configurado'}\n"
    )
    await update.message.reply_text(status, parse_mode="Markdown")

async def cmd_routes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    routes = (
        "*Estaciones Troncales Transmilenio:*\n\n"
        "*Linea K (Norte):*\n"
        "- Portal Norte\n- Calle 161\n- Calle 146\n- Calle 127\n"
        "- Calle 100\n- Calle 85\n- Calle 76\n\n"
        "*Linea B (Sur):*\n"
        "- Portal Sur\n- Guatoque\n- General Santander\n"
        "- Calle 38\n- Calle 17\n\n"
        "*Linea C (Occidente):*\n"
        "- Portal 80\n- Suba\n- Calle 80\n\n"
        "*Linea D (Oriente):*\n"
        "- Portal Eldorado\n- Aeropuerto\n\n"
        "_Para rutas SITP, pregunta directamente tu origen y destino._"
    )
    await update.message.reply_text(routes, parse_mode="Markdown")

async def cmd_bloqueo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Uso: /bloqueo <nombre_estacion>")
        return
    station = " ".join(context.args).lower().strip()
    BLOCKED_STATIONS[station] = time.time() + 7200
    await update.message.reply_text(f"🚧 ¡Reporte recibido! He bloqueado temporalmente la estación '{station.title()}'. El bot ruteará a los usuarios por vías alternas durante las próximas 2 horas.")

async def process_route(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message.text
    
    msg_processing = await update.message.reply_text("Buscando la mejor ruta...", parse_mode="Markdown")
    
    entities = await extract_entities_with_ollama(message)
    origin = entities.get("origin")
    destination = entities.get("destination")
    user_time = entities.get("time") or "now"
    preferences = entities.get("preferences")

    if not origin or not destination:
        err_doc = {
            "route_summary": "No pude identificar origen y destino",
            "steps": ["Por favor, especifica claramente tu punto de origen y destino"],
            "estimated_time": "-",
            "distance": "-",
        }
        await msg_processing.edit_text(format_route_response(err_doc), parse_mode="Markdown")
        return

    maps_results = await get_distance_and_time(origin, destination, user_time)
    
    all_route_docs = []
    
    for idx, maps_data in enumerate(maps_results):
        if "error" in maps_data:
            all_route_docs.append({
                "route_summary": maps_data.get("route_summary", "❌ Problema de cobertura"),
                "steps": maps_data.get("steps", [maps_data["error"]]),
            })
            continue

        route_data = calculate_optimal_route(
            origin=origin,
            destination=destination,
            google_maps_data=maps_data,
            time_of_day=user_time
        )

        transit_details = maps_data.get("transit_details", [])
        next_bus_text = "Sin telemetría en vivo (posible ruta cerrada/desactualizada)"
        
        if transit_details:
            first_transit = transit_details[0]
            dep_unix = first_transit.get("departure_time_unix")
            if dep_unix:
                minutes_left = int((dep_unix - time.time()) / 60)
                if minutes_left < 0:
                    next_bus_text = "El bus ya partió"
                elif minutes_left == 0:
                    next_bus_text = "¡El bus está llegando en este instante!"
                else:
                    next_bus_text = f"estimado en {minutes_left} min"

        route_summary = f"Tipo: {route_data['route_type'].upper()}\n"
        route_summary += f"Próximo bus: {next_bus_text}"

        result_doc = {
            "route_summary": route_summary,
            "steps": route_data["steps"],
            "estimated_time": route_data["estimated_time"],
            "distance": route_data["distance"],
        }
        all_route_docs.append(result_doc)

    global_doc = {
        "header": f"Ruta: {origin.title()} -> {destination.title()}",
        "options": all_route_docs
    }
    
    decorations = []
    if WEATHER_CACHE.get("is_raining"): decorations.append("🌧️ MODO LLUVIA ACTIVO")
    if is_night_time(): decorations.append("🌙 MODO NOCHE SEGURO")
    
    current_t = time.time()
    active_manual = [k for k, v in BLOCKED_STATIONS.items() if v > current_t]
    active_news = [k for k, v in NEWS_BLOCK_CACHE.get("stations", {}).items() if v > current_t]
    
    if active_manual or active_news:
        dec_str = "⚠️ RUTEO EVADIENDO BLOQUEOS"
        b_list = []
        for b in active_manual: b_list.append(b.title() + " (Usuarios)")
        for b in active_news: b_list.append(b.title() + " (Noticias)")
        if b_list:
            dec_str += f"\n  ⛔ Evitadas: {', '.join(b_list)}"
        decorations.append(dec_str)

    if decorations:
        global_doc["header"] = "\n\n".join(decorations) + "\n\n" + global_doc["header"]

    try:
        await msg_processing.edit_text(format_route_response(global_doc), parse_mode="Markdown")
    except Exception as e:
        print(f"Error editing message: {e}")
        await update.message.reply_text(format_route_response(global_doc), parse_mode="Markdown")

def main():
    if not TELEGRAM_BOT_TOKEN:
        print("ERROR: TELEGRAM_BOT_TOKEN no esta configurado.")
        return

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("help", cmd_start))
    application.add_handler(CommandHandler("status", cmd_status))
    application.add_handler(CommandHandler("routes", cmd_routes))
    application.add_handler(CommandHandler("bloqueo", cmd_bloqueo))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_route))

    print("=" * 60)
    print("BOT TELEGRAM TRANSMILENIO/SITP - DOCKER")
    print("=" * 60)
    print(f"Ollama URL: {OLLAMA_BASE_URL}")
    print(f"Model: {OLLAMA_MODEL}")
    print(f"Google Maps: {'Configurado' if GOOGLE_MAPS_API_KEY else 'No configurado'}")
    print("=" * 60)
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
