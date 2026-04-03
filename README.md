# Bogotá Public Transit Route Bot (TransMilenio/SITP)

Distributed IoT system for public transit route consultation in Bogotá, Colombia. The system integrates an ESP32 microcontroller, Telegram messaging platform, and a proxy server with natural language processing capabilities.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [System Requirements](#system-requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [API Reference](#api-reference)
- [Troubleshooting](#troubleshooting)

---

## Architecture Overview

```
┌─────────────────┐     ┌─────────────────┐     ┌──────────────────────────┐
│   Telegram      │     │   ESP32         │     │   Proxy Server (Python)  │
│   User          │────▶│   (WiFi)        │────▶│   - FastAPI              │
│                 │     │                 │     │   - Ollama (LLM)         │
└─────────────────┘     └─────────────────┘     │   - Google Maps API      │
                                                │   - ArcGIS Transmilenio  │
                                                └────────────┬─────────────┘
                                                             │
                     ┌───────────────────────────────────────┼──────────────┐
                     │                                       ▼              │
                     │  ┌──────────────┐  ┌──────────────┐  ┌────────────┐  │
                     │  │   Ollama     │  │   Google     │  │  ArcGIS    │  │
                     │  │   (LLM)      │  │   Maps       │  │  API       │  │
                     │  └──────────────┘  └──────────────┘  └────────────┘  │
                     └──────────────────────────────────────────────────────┘
```

### System Components

| Component | Function |
|-----------|----------|
| **ESP32** | Manages WiFi connectivity, receives Telegram messages via long polling, forwards context to proxy server |
| **Proxy Server** | Orchestrates LLM inference, external API calls, and route computation logic (Python/FastAPI) |
| **Ollama** | Local LLM for natural language entity extraction (origin, destination, time preferences) |
| **Google Maps API** | Provides accurate distance calculations and transit duration estimates |
| **ArcGIS Transmilenio** | Official data source for trunk station locations and metadata |

### Design Rationale

A proxy-based architecture was selected over embedded-only processing due to:

1. **Memory Constraints**: ESP32 free heap (~300KB) insufficient for LLM inference
2. **SSL/TLS Overhead**: Multiple secure connections exhaust embedded resources
3. **Maintainability**: Centralized logic simplifies updates and API key rotation
4. **Scalability**: Proxy can serve multiple ESP32 devices simultaneously

---

## System Requirements

### Hardware

| Item | Specification |
|------|---------------|
| Microcontroller | ESP32-WROOM or ESP32-WROVER (PSRAM recommended) |
| Power | 5V USB or regulated 3.3V supply |
| Network | 2.4GHz WiFi (802.11 b/g/n) |

### Software - Embedded

| Dependency | Version |
|------------|---------|
| PlatformIO Core | >= 6.0 |
| ArduinoJson | >= 7.0 |
| UniversalTelegramBot | >= 1.3 |
| NTPClient | >= 3.2 |

### Software - Proxy Server

| Dependency | Version |
|------------|---------|
| Python | 3.9+ |
| FastAPI | 0.109 |
| Uvicorn | 0.27 |
| Ollama | Latest (with llama3.2 model) |

---

## Installation

### 1. Proxy Server Setup

```bash
cd proxy_server

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp ../.env.example .env
# Edit .env with valid credentials
```

### 2. Ollama Installation

```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh   # Linux/macOS
# Download installer from https://ollama.ai for Windows

# Pull recommended model
ollama pull llama3.2

# Start Ollama service
ollama serve
```

### 3. ESP32 Firmware

```bash
# Using PlatformIO CLI
cd esp32_telegram_bot
pio run --target upload

# Or use VS Code PlatformIO extension:
# 1. Open esp32_telegram_bot folder
# 2. Copy src/secrets.h.example to src/secrets.h
# 3. Edit secrets.h with credentials
# 4. Click Build and Upload
```

### 4. Environment Configuration

Edit `.env` in `proxy_server/`:

```env
TELEGRAM_BOT_TOKEN=1234567890:AAFgH8kL9mN0pQrStUvWxYz
OLLAMA_BASE_URL=http://localhost:11434
GOOGLE_MAPS_API_KEY=AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

---

## Configuration

### Telegram Bot Token

1. Open Telegram and search for `@BotFather`
2. Send `/newbot` command
3. Follow prompts to name your bot
4. Copy the provided API token to `.env`

### Google Maps API Key

1. Navigate to [Google Cloud Console](https://console.cloud.google.com/)
2. Create or select a project
3. Enable "Directions API" and "Maps JavaScript API"
4. Create credentials -> API Key
5. Restrict key by HTTP referrer (recommended)

### Ollama Verification

```bash
# Verify Ollama service is running
curl http://localhost:11434/api/tags

# Test model inference
ollama run llama3.2 "Hello, how are you?"
```

---

## Usage

### 1. Start Proxy Server

```bash
cd proxy_server
python app.py

# Server starts on http://0.0.0.0:5000
# API documentation available at http://localhost:5000/docs
```

### 2. Flash ESP32 Firmware

```bash
cd esp32_telegram_bot
pio run --target upload
```

### 3. Interact via Telegram

1. Search for your bot in Telegram
2. Send `/start` to display welcome message
3. Submit route requests in natural language

### Available Commands

| Command | Description |
|---------|-------------|
| `/start` | Display welcome message and usage instructions |
| `/status` | Show system status (WiFi, memory, uptime) |
| `/routes` | List main trunk stations by line |

### Query Examples

```
From Calle 100 to Portal Norte
What bus do I take from my house to downtown?
Route from Suba to Calle 100 at 8am
From Portal Sur to Airport
```

---

## API Reference

### POST /api/route

Calculate optimal route for a transit request.

**Request Body:**
```json
{
  "message": "From Calle 100 to Portal Norte",
  "chat_id": "123456789",
  "timestamp": "2026-04-03T08:00:00-05:00",
  "location": "Bogota, Colombia"
}
```

**Response:**
```json
{
  "route_summary": "Route: Calle 100 -> Portal Norte\nType: TRONCAL\nFrequency: every 5 min",
  "steps": [
    "Walk to nearest station at Calle 100",
    "Validate card at turnstile",
    "Board bus on correct platform",
    "Exit at Portal Norte station",
    "Walk to final destination"
  ],
  "estimated_time": "25 minutes",
  "distance": "8.5 km",
  "cost": "$3,550 COP",
  "recommendations": "Use correct platform | Rush hour: expect delays",
  "alternatives": [
    "Direct SITP route (~15-20 min longer)",
    "Taxi/Uber: ~$15,000-25,000 COP, 15-20 min",
    "Bicycle: use bike lane if available"
  ]
}
```

### GET /api/status

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-04-03T13:00:00",
  "ollama_url": "http://localhost:11434",
  "model": "llama3.2",
  "google_maps_configured": true
}
```

### GET /api/stations

Retrieve list of all trunk stations.

**Response:**
```json
{
  "stations": [
    {"name": "Portal Norte", "line": "K", "lat": 4.7089, "lng": -74.0721},
    ...
  ]
}
```

---

## Project Structure

```
agente_tm/
├── esp32_telegram_bot/
│   ├── src/
│   │   ├── main.cpp              # ESP32 firmware
│   │   ├── secrets.h             # Credentials (do not commit)
│   │   └── secrets.h.example     # Credential template
│   └── platformio.ini            # PlatformIO configuration
│
├── proxy_server/
│   ├── app.py                    # FastAPI server
│   ├── transmilenio_data.py      # ArcGIS data fetcher
│   ├── requirements.txt          # Python dependencies
│   └── run.sh                    # Startup script
│
├── .env.example                  # Environment variable template
├── .gitignore                    # Git ignore rules
├── README.md                     # This file
└── ARQUITECTURA.md               # Detailed architecture documentation
```

---

## Troubleshooting

### ESP32 WiFi Connection Failures

| Symptom | Cause | Resolution |
|---------|-------|------------|
| No connection | 5GHz network | ESP32 only supports 2.4GHz |
| Authentication failure | Incorrect credentials | Verify SSID/password in `secrets.h` |
| Weak signal | Distance from router | Use WiFi extender or relocate device |

### Proxy Server Issues

| Symptom | Cause | Resolution |
|---------|-------|------------|
| Timeout on route requests | Ollama not running | Execute `ollama serve` |
| HTTP 500 errors | Missing API keys | Verify `.env` configuration |
| Port binding failure | Port 5000 in use | Change `PROXY_SERVER_PORT` |

### Ollama Performance

| Symptom | Cause | Resolution |
|---------|-------|------------|
| Slow inference | Insufficient RAM | Use smaller model (e.g., `tinyllama`) |
| Connection refused | Service not started | Check `ollama serve` status |
| Model not found | Model not downloaded | Execute `ollama pull llama3.2` |

---

## Fare Structure (2026)

| Service Type | Fare (COP) |
|--------------|------------|
| TransMilenio (Trunk) | $2,950 |
| SITP (Zonal) | $2,600 |
| Integrated (TM + SITP within 1hr) | $3,950 |

---

## Security Considerations

1. **Credential Management**: Never commit `secrets.h` or `.env` to version control
2. **API Key Restrictions**: Limit Google Maps API key by referrer and enable billing alerts
3. **Network Segmentation**: Consider isolated IoT VLAN for ESP32 devices
4. **Chat Authorization**: Implement chat_id whitelist for production deployments
5. **SSL/TLS**: Use `setInsecure()` only for development; implement certificate validation in production

---

## License

MIT License - See LICENSE file for details.

---

## Contributing

Contributions are welcome. Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request
