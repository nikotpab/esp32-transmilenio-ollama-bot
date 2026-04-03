# Arquitectura del Sistema: Bot TransMilenio Dinámico

Este documento técnico de ingeniería despliega la arquitectura end-to-end de las micro-integraciones del Agente en Docker para transitar Bogotá y superar las propias limitantes de APIs de proveedores globales. 

## Diagrama Funcional de Capas

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                                INTERNET / NUBE                               │
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
│  │    │     Telegram Handler    │ ◄───────────► │  Memoria Caché     │    │  │
│  │    │    (python-telegram)    │               │  (Bloqueos/Clima)  │    │  │
│  │    └────────────┬────────────┘               └────────────────────┘    │  │
│  │                 │                                                      │  │
│  │    ┌────────────▼────────────┐               ┌────────────────────┐    │  │
│  │    │     Motor de Algoritmo  │ ◄───────────► │ Inyector Vagones   │    │  │
│  │    │ (Noche/Lluvia/Bloqueos) │               │ y Micro-Ruteos     │    │  │
│  │    └────────────┬────────────┘               └────────────────────┘    │  │
│  │                 │                                                      │  │
│  │  ┌──────────────┼─────────────────────────────────────────────┐        │  │
│  │  │              ▼                     Llamadas Nativas API    │        │  │
│  │  │   ┌────────────────────┐                                   │        │  │
│  │  │   │ Ollama LLM Local   │ (Extrae Intención del Usuario)    │        │  │
│  │  │   └────────────────────┘                                   │        │  │
│  │  └────────────────────────────────────────────────────────────┘        │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Módulo de Escaneo Comunitario (El "Waze" del Sistema)
Google Maps tradicionalmente se demora 30+ minutos en advertir un cierre social sobre una troncal. Para remediar esto, el bot cuenta un algoritmo dual:

1. **Scraping RSS Pasivo (`update_live_news_blocks`):** Se ejecuta un *XML Fetcher* contra servidores de Google News restringido a notas de 24hrs sobre "Transmilenio". Si el motor capta titulares publicando bloqueos que mencionan el título de la estación (Ej "Obras en Portal Eldorado"), castiga automáticamente los grafos hacia esa ruta por 2 horas sin intervención humana.
2. **Escucha Activa:** Los usuarios pueden utilizar `/bloqueo [Estación]` con el celular dentro de un bus detenido para que este ecosistema se comparta horizontalmente hacia todos los demás usuarios de Telegram solicitando rutas en tiempo real.

## Motor Físico y Ruteo Predictivo

### 1. Extractor LLM Seguro (Ollama)
Cualquier mensaje directo es enviado cifrado hacia un servidor puente Docker ancla al `host.docker.internal` comunicándose con `Ollama`. Aísla la solicitud para encontrar si el usuario pidió viajar "mañana", "noche" o "ya", e identificar orígenes desordenados en *diccionarios puros* JSON.

### 2. Conversión Unix de Agendas y Ventanas Operativas 
El algoritmo detecta contextos de tiempo arrojados en NLP como "Tarde" o "Mañana". Se procesa en una conversión cruzando el desvío `UTC-5` de Bogotá para generar estampados **Unix Timestamps exactos**, para forzar a la API Direcciones de Google Networks a ceñir los buses netamente dentro de los tiempos físicos de sus operaciones y desechar buses no funcionales.

### 3. Interceptor Meteorológico y Factor de Noche
- Si `open-meteo` devuelve >0 mm de probabilidad de caída de agua, las fórmulas matemáticas de pesos penalizan fuertemente transbordos largos.
- Si el reloj interno Bogotano indica hora pico de inseguridad (>21:00 PM), una condición inyecta puntajes drásticos bloqueando el retorno prioritario de buses azules de SITP y dictaminando usar circuitos del carril exclusivo central, por lo general resguardados mejor bajo faroles de techo alto.

### 4. Diccionario Intrínseco de Micro-Vagones
Se rebasaron los alcances genéricos de Google por un `VAGONES_COMPLEJOS` Dictionary Injector. Cuando una topología se detecta originándose desde una super-estación tipo Calle 100, la consola inyectará visualmente el Túnel/Carpa exacta para erradicar las molestias de usuarios perdidos.

---

## Arquitectura de Datos Dinámica
Durante el armado de una respuesta se construye un "Documento de Ruta", cuyo Header consolida toda la información cruzada.
Ejemplo:
```json
{
  "header": "⚠ RUTEO EVADIENDO BLOQUEOS\n ⛔ Evitadas: Portal Americas (Noticias) | \n\n Ruta: Ricaurte -> Portal Norte",
  "options": [
    {
      "route_summary": "TRONCAL - Proximo bus: en 12 min",
      "steps": ["..."]
    }
  ]
}
```

## Control de Calidad
- Este ecosistema asegura que la memoria esté controlada por Limpiezas Garbage Collector asíncronas para el bot en Python, evitando colapsos locales dentro del sistema subyacente.
