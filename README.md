# Bogotá Transit AI Copilot (TransMilenio/SITP)

A specialized, completely local Python-based Telegram Bot running within a Dockerized ecosystem. Designed exclusively for Bogota's complex transit network, this orchestrator integrates Privacy-First NLP, temporal routing parities, heuristic micro-routing dictionaries, and background XML scraping to dynamically adapt suggestions to real-time events.

## Architectural Highlights

- **Privacy-Preserving NLP Engine:** Leverages a local `llama3.2` instance via Ollama. It extracts origins, destinations, and temporal constraints from conversational interactions natively, bypassing cloud inference latency and preventing personal routing telemetry exposition to third-party endpoints.
- **Automated RSS Outage Indexing (Waze-like Heuristic):** The system circumvents slow API notifications by aggressively scraping Google News RSS feeds every 10 minutes. If terms like 'blockades', 'riots', or 'closures' intersect with the local topology dictionary, the routing algorithm introduces an absolute constraint rendering affected segments mathematically inaccessible for all queries.
- **Micro-Routing (Intramural Station Topologies):** Addresses one of the major caveats belonging to standard GIS mapping platforms by pinpointing exact underground tunnels or BRT (Bus Rapid Transit) loading wagons (e.g., _"Board the G43 at Wagon 2"_), avoiding user dead-ends within mega-stations.
- **Meteorological & Chronological Route Penalty:**
  - **Open-Meteo Integration:** A caching daemon tracks precipitation levels over Bogota. If rain thresholds are surpassed, walking edges natively provided by Google Maps Directions API weighing beyond 400 meters are heavily penalized, prioritizing direct point-to-point trunk connectivity.
  - **Security Safe-Mode:** Between 21:00 and 05:00 UTC-5, the engine natively forces strict adherence to trunk roads (BRTs), isolating users from unlit zonal connections (SITP routing) for enhanced physical safety.

_(For an extensive structural breakdown, refer to [ARQUITECTURA.md](ARQUITECTURA.md))._

## System Requirements

- **Docker** and **Docker Compose**
- **Ollama** installed on the host daemon equipped with the `llama3.2` model.
- A **Telegram Bot API Token** provisioned via `@BotFather`.
- A **Google Maps API Key** strictly holding `Directions API` clearance.

## Deployment Lifecycle

### 1. Environment Declaration
Clone the repository and map your persistent environmental tokens:
```bash
cp .env.example .env
```
Populate `.env` with your secure access parameters.

### 2. Invoke Local Models
Ensure your host machine is exposing its LLM inference gateway:
```bash
ollama serve
ollama pull llama3.2
```

### 3. Container Initialization
Bring up the Docker abstraction:
```bash
docker compose up --build -d
```
The node is instantly bootstrapped and asynchronously listening onto Telegram's webhook polling interfaces.

## Operational CLI

| Command Action | Handler Definition |
|---------|-------------|
| `/start` | Render platform handshake and instructional scope. |
| `/status` | Ping and summarize active services (Container mapping, Ollama ping, API states). |
| `/routes` | Expose the static dictionary arrays sorted by the Red Trunk BRT lines. |
| `/bloqueo` | Manual user-provisioning route closures. Injects a 7200s TTL station blockade. |

### Semantic Abstraction Scenarios
The AI understands raw conversational intent without regex boundaries:

> *"Need to get from Calle 100 to Portal Norte"*
>
> *"How do I commute right now from my house to the airport?"*
>
> *"Route from Ricaurte to Calle 76 tonight"*

## License & Security Posture
- This system enforces LLM evaluation over the `host.docker.internal` network barrier natively. Data is neither persisted nor analyzed externally.
- Ensure to restrict your `Google Maps API` requests context directly on Google Cloud Console utilizing referrers to prevent cost leakages. 
- Licensed under standard MIT bounds. See `LICENSE` for expanded literature.
