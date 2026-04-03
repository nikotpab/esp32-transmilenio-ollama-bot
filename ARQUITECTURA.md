# System Architecture: Dynamic TransMilenio Bot Orchestrator

This technical document outlines the end-to-end architecture of the Dockerized Bogota Transit Agent. The system implements a robust micro-integration footprint designed to supersede generic global API providers by establishing city-contextualized data flows, chronological parity, and crowdsourced live heuristics.

## Functional Layer Diagram

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                                INTERNET / CLOUD                              │
│                                                                              │
│  ┌────────────┐    ┌─────────────┐   ┌─────────────────┐   ┌──────────────┐  │
│  │  Telegram  │    │ Google Maps │   │ Open-Meteo API  │   │ Google News  │  │
│  │   Cloud    │    │  (Transit)  │   │   (Lat/Lon)     │   │     RSS      │  │
│  └──────┬─────┘    └──────┬──────┘   └───────┬─────────┘   └──────┬───────┘  │
│         │                 │                  │                    │          │
│         ▼ Polling         ▼ JSON             ▼ Precip.%           ▼ XML News │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │                           BOT CONTAINER (Docker)                       │  │
│  │                                                                        │  │
│  │    ┌─────────────────────────┐               ┌────────────────────┐    │  │
│  │    │     Telegram Handler    │ ◄───────────► │   Cache Memory     │    │  │
│  │    │    (python-telegram)    │               │  (Blockades/Rain)  │    │  │
│  │    └────────────┬────────────┘               └────────────────────┘    │  │
│  │                 │                                                      │  │
│  │    ┌────────────▼────────────┐               ┌────────────────────┐    │  │
│  │    │    Algorithmic Engine   │ ◄───────────► │  Wagon Injector &  │    │  │
│  │    │  (Night/Weather/Blocks) │               │   Micro-Routing    │    │  │
│  │    └────────────┬────────────┘               └────────────────────┘    │  │
│  │                 │                                                      │  │
│  │  ┌──────────────┼─────────────────────────────────────────────┐        │  │
│  │  │              ▼                       Native API Calls      │        │  │
│  │  │   ┌────────────────────┐                                   │        │  │
│  │  │   │ Ollama LLM Local   │ (Extracts User Intent)            │        │  │
│  │  │   └────────────────────┘                                   │        │  │
│  │  └────────────────────────────────────────────────────────────┘        │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Crowdsourced Heuristics Module (The "Waze" Subsystem)
Traditional GIS APIs like Google Maps often experience high latency (30+ minutes) when notifying closures across Bogota's trunk infrastructure. To mitigate this, the bot deploys a dual-algorithm approach:

1. **Passive RSS Scraping (`update_live_news_blocks`):** An asynchronous XML Fetcher periodically polls Google News servers restricted to a rolling 24-hour window analyzing "TransMilenio" occurrences. If the engine intercepts aggregated headlines identifying closures structurally coupled to our localized station dictionary (e.g., _"Roadworks affecting Portal Eldorado"_), it natively assigns a heavy duration penalty to all edges intersecting that specific node for a synchronized TTL interval of 2 hours.
2. **Active Telemetry:** Passengers experiencing sudden delays can execute the `/bloqueo [Station]` command through their handheld devices inside a grounded bus. This triggers an instant horizontal topology quarantine across the ecosystem, subsequently diverting any future passenger requesting interacting routes away from the blocked perimeter.

## Physics Engine and Predictive Routing

### 1. Secure NLP Orchestration (Local Ollama)
Any inbound conversation stream is intercepted and relayed onto a bridged Docker host layer (`host.docker.internal`), initiating JSON-bound queries strictly with a local `Ollama` framework. It filters temporal contexts (e.g. "tomorrow", "night") and translates messy geographical semantics into raw structured dictionary arrays, effectively sandboxing traveler telemetry off untrusted cloud environments.

### 2. Chronological Operations and Unix Conversion
As the NLP returns vague temporal bounds, an alignment daemon intercepts Bogota's spatial standard (`UTC-5`) and converts textual data into strict numerical **Unix Timestamps**. Supplying these standardized stamps to Google's Transit API overrides phantom-buses, natively dictating the solver to acknowledge operational shifts and closed gateways.

### 3. Meteorological Sensor and Nocturnal Multipliers
- If `open-meteo` telemetry yields `>0.0 mm` probability of localized precipitation, mathematical weights aggressively penalize pedestrian connections mapping over 400 linear meters.
- The internal chronometer observes vulnerable peak hours (`>21:00 PM`). A rigid mathematical rule inflates penalties against solitary urban fleet buses (SITP network), forcing the final topological path matrix to favor BRT (Trunk) indoor infrastructure protected by illuminated concourses.

### 4. Micro-Routing Enclosed Topologies
To address the generic limitations of conventional waypoint directives, the engine maintains a deep mapping matrix (`VAGONES_COMPLEJOS`). When generating textual step-by-step guidance, the processor identifies high-complexity transport nodes (e.g., _Calle 100_ or _Ricaurte_) and conditionally appends tunnel directions, canopy designations, and precise wagon loading areas to alleviate passenger disorientation within expansive structures.

---

## Dynamic State Topology
During traversal generation, an overriding "Route Document" dictates interaction schemas.

```json
{
  "header": "⚠ ROUTE EVADING CLOSURES\n ⛔ Avoided: Portal Americas (News Broadcast) | \n\n Ruta: Ricaurte -> Portal Norte",
  "options": [
    {
      "route_summary": "TRUNK - Next bus: arriving in 12 min",
      "steps": ["..."]
    }
  ]
}
```

## Component Quality Assurance
- Routine state flushing methodologies utilize asynchronous Python Garbage Collectors protecting background RAM limits, guaranteeing steady state machine execution under heavy Telegram polling throughput.
