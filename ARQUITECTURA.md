# Architecture Documentation

## System Overview

This document describes the architecture of a distributed IoT system for public transit route consultation in Bogota, Colombia. The system combines an ESP32 microcontroller, Telegram messaging platform, a proxy server with natural language processing, and multiple external data sources.

## Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────────┐
│                           INTERNET                                       │
│                                                                          │
│  ┌─────────────┐                                                         │
│  │   Telegram  │                                                         │
│  │   Cloud     │                                                         │
│  └──────┬──────┘                                                         │
│         │ Bot API                                                        │
│         ▼                                                                  │
│  ┌─────────────────────────────────────────────────────────────────┐     │
│  │                    LOCAL NETWORK (WiFi)                          │     │
│  │                                                                   │     │
│  │  ┌─────────────┐         ┌──────────────────┐                    │     │
│  │  │    ESP32    │────────▶│   Proxy Server   │                    │     │
│  │  │             │  HTTP   │   (Python/Fast)  │                    │     │
│  │  │  - WiFi     │  JSON   │                  │                    │     │
│  │  │  - Telegram │         │  - NLP (Ollama)  │                    │     │
│  │  │  - HTTP     │         │  - Google Maps   │                    │     │
│  │  └─────────────┘         │  - ArcGIS        │                    │     │
│  │                          └─────────┬────────┘                    │     │
│  │                                    │                               │     │
│  └────────────────────────────────────┼───────────────────────────────┘     │
│                                       │                                      │
│         ┌─────────────────────────────┼─────────────────────────────┐       │
│         │                             ▼                               │       │
│         │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │       │
│         │  │   Ollama     │  │   Google     │  │   ArcGIS     │      │       │
│         │  │   (LLM)      │  │   Maps API   │  │   API        │      │       │
│         │  │  Port 11434  │  │  Directions  │  │  Stations    │      │       │
│         │  └──────────────┘  └──────────────┘  └──────────────┘      │       │
│         └─────────────────────────────────────────────────────────────┘       │
└──────────────────────────────────────────────────────────────────────────┘
```

## Data Flow

### 1. Message Reception (ESP32 -> Proxy)

```
Telegram User
      │
      ▼
┌─────────────────────────┐
│ 1. User sends:          │
│    "From Calle 100 to   │
│     Portal Norte"       │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ 2. ESP32 receives       │
│    message via Telegram │
│    Bot API (Long Poll)  │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ 3. ESP32 sends HTTP POST│
│    to Proxy Server:     │
│    {                    │
│      "message": "...",  │
│      "chat_id": "123",  │
│      "timestamp": "..." │
│    }                    │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ 4. Proxy receives       │
│    request              │
└─────────────────────────┘
```

### 2. NLP Processing (Proxy -> Ollama -> Proxy)

```
┌─────────────────────────┐
│ 5. Proxy constructs     │
│    prompt for Ollama:   │
│    "Extract entities    │
│    from: 'From Calle    │
│    100 to Portal Norte'"│
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ 6. Ollama processes and │
│    returns JSON:        │
│    {                    │
│      "origin": "Calle   │
│        100",            │
│      "destination":     │
│        "Portal Norte",  │
│      "time": "now"      │
│    }                    │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ 7. Proxy parses         │
│    entities             │
└─────────────────────────┘
```

### 3. Route Query (Proxy -> Google Maps -> Proxy)

```
┌─────────────────────────┐
│ 8. Proxy queries        │
│    Google Maps:         │
│    /api/directions?     │
│    origin=Calle+100     │
│    destination=Portal   │
│    +Norte&mode=transit  │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ 9. Google Maps returns  │
│    route, distance,     │
│    duration, steps      │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ 10. Proxy calculates    │
│     optimal route       │
│     (TM + SITP)         │
└─────────────────────────┘
```

### 4. Response to User (Proxy -> ESP32 -> Telegram)

```
┌─────────────────────────┐
│ 11. Proxy sends JSON    │
│     to ESP32:           │
│     {                   │
│       "route_summary":  │
│       "steps": [...],   │
│       "estimated_time": │
│       "cost": ...       │
│     }                   │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ 12. ESP32 formats and   │
│     sends to Telegram   │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ 13. User receives:      │
│     Route: Calle 100    │
│     -> Portal Norte     │
│     Steps:              │
│     1. Walk to...       │
│     2. Validate card    │
│     Time: 25 min        │
│     Cost: $2,950        │
└─────────────────────────┘
```

## Component Details

### ESP32 Firmware

**Responsibilities:**
- WiFi connectivity (STA mode)
- Telegram message polling (Long Polling)
- HTTP POST context transmission to Proxy
- Response reception and formatting
- Memory and state management

**Key Libraries:**
| Library | Purpose |
|---------|---------|
| UniversalTelegramBot | Telegram Bot API client |
| ArduinoJson | JSON serialization/deserialization |
| HTTPClient | HTTP requests to Proxy |
| NTPClient | Time synchronization (Bogota UTC-5) |

**Memory Optimizations:**
- `StaticJsonDocument` instead of `DynamicJsonDocument`
- SSL insecure mode (`setInsecure()`) for RAM conservation
- Heap check every 10 seconds
- LED status indicator for visual debugging

### Proxy Server (Python/FastAPI)

**Responsibilities:**
- REST API for ESP32 clients
- Service orchestration (Ollama, Google Maps, ArcGIS)
- Business logic (route calculation, fares, transfers)
- Station data caching

**Endpoints:**
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/route` | POST | Calculate route from message |
| `/api/status` | GET | System health check |
| `/api/stations` | GET | List of trunk stations |

**Modules:**
```
proxy_server/
├── app.py                 # Main server + endpoints
├── transmilenio_data.py   # ArcGIS fetcher + cache
├── requirements.txt       # Python dependencies
└── run.sh                 # Startup script
```

### Ollama (Local LLM)

**Purpose:** Extract entities from natural language messages.

**Prompt Template:**
```python
prompt = f"""
You are an expert assistant for Bogota public transit.
Extract entities from the following user request.

Request: "{message}"

Return ONLY valid JSON with this format:
{{
    "origin": "origin location",
    "destination": "destination location",
    "time": "specific time or 'now'",
    "date": "specific date or 'today'",
    "preferences": ["fast", "cheap"] or null
}}
"""
```

**Recommended Models:**
| Model | Size | RAM Required | Speed |
|-------|------|--------------|-------|
| llama3.2 | 3B | 4GB | Fast |
| mistral | 7B | 8GB | Medium |
| phi3 | 3.8B | 4GB | Fast |

## Data Schema

### Request (ESP32 -> Proxy)

```json
{
  "message": "From Calle 100 to Portal Norte at 8am",
  "chat_id": "123456789",
  "timestamp": "2026-04-03T08:00:00-05:00",
  "location": "Bogota, Colombia"
}
```

### Response (Proxy -> ESP32)

```json
{
  "route_summary": "Route: Calle 100 -> Portal Norte\nType: TRONCAL\nFrequency: every 5 min",
  "steps": [
    "Walk to Calle 100 station",
    "Validate card at turnstile",
    "Board bus on North platform",
    "Exit at Portal Norte",
    "Walk to final destination"
  ],
  "estimated_time": "25 minutes",
  "distance": "8.5 km",
  "cost": "$2,950 COP",
  "recommendations": "Use correct platform | Rush hour: expect delays",
  "alternatives": [
    "Direct SITP route (~15-20 min longer)",
    "Taxi/Uber: ~$15,000-25,000 COP, 15-20 min",
    "Bicycle: use bike lane if available"
  ],
  "raw_entities": {
    "origin": "Calle 100",
    "destination": "Portal Norte",
    "time": "morning",
    "date": "today",
    "preferences": null
  }
}
```

## Security

### Credential Files

| File | Content | Commit to Git? |
|------|---------|----------------|
| `secrets.h` | ESP32 credentials | NEVER |
| `.env` | Proxy environment variables | NEVER |
| `.env.example` | Template | YES |

### Recommendations

1. **Telegram Bot Token**: Regenerate if accidentally exposed
2. **Google Maps API Key**: Restrict by HTTP referrer, enable billing alerts
3. **WiFi**: Use separate network for IoT devices if possible
4. **Chat Authorization**: Implement chat_id whitelist for production

## Scalability

### Future Enhancements

1. **WebSocket**: Replace HTTP polling for lower latency
2. **Redis Cache**: Cache frequently requested routes
3. **Load Balancer**: Multiple proxy server instances
4. **Database**: PostgreSQL for route history and analytics
5. **Web Dashboard**: Monitoring and statistics interface

## Troubleshooting

### Common Issues

| Symptom | Probable Cause | Resolution |
|---------|---------------|------------|
| ESP32 no WiFi | 5GHz network | Use 2.4GHz network |
| Proxy timeout | Ollama not running | Execute `ollama serve` |
| Incorrect responses | Model too small | Use llama3.2 or larger |
| Low ESP32 memory | JSON too large | Reduce response size |

## References

- [Telegram Bot API](https://core.telegram.org/bots/api)
- [Ollama API Documentation](https://github.com/ollama/ollama/blob/main/docs/api.md)
- [Google Maps Directions API](https://developers.google.com/maps/documentation/directions/overview)
- [TransMilenio Open Data](https://datosabiertos.transmilenio.gov.co/)
- [ESP32 Arduino Core](https://docs.espressif.com/projects/arduino-esp32/en/latest/)
