# Bogota Public Transit Route Bot (TransMilenio/SITP)

Un Bot de Telegram completamente local, programado en Python y desplegado en Docker, especializado en ofrecer ruteo inteligente nativo para Bogotá. Integra IA local, scraping de noticias en tiempo real, conectividad climática y enrutamiento inteligente por niveles.

## Características Revolucionarias
- **Motor de PLN Privado:** Utiliza `Llama 3.2` vía Ollama en *localhost* para extraer origen, destino e intención sin enviar datos del viaje del usuario a modelos cloud no confiables.
- **Micro-Enrutamiento Inter-Estacional:** A diferencia de Google Maps, el bot indica explícitamente a los usuarios el **Vagón de la estación** exacto (Ej: "Aborda el G43 en el Vagón 2") en estaciones caóticas y masivas.
- **Waze Transmilenio (Scraping de Noticias):** Subrutinas en segundo plano consultan silenciosamente portales RSS de noticias cada 10 minutos (Google News Feed). Si algoritmos detectan palabras clave como "obras", "cierre" o "bloqueo" asociadas a una estación oficial de Transmilenio, el nodo **bloquea automáticamente las búsquedas** para aislar virtualmente la ruta afectada antes de que el usuario lo intente, todo sin reportes manuales.
- **Ruteo Sensible al Clima:** Consume la API satelital gratuita de `open-meteo` cada 15 minutos en memoria de contingencia. Si el milimetraje de precipitación es positivo de su lugar, el bot penaliza radicalmente trayectos que impliquen largos enlaces peatonales forzando al usuario a transbordar cerrado. 
- **Modo "Noche Segura":** Parseo estructural de UNIX al interior de `Google Maps API`. Entre las 9:00 PM y las 5:00 AM, desecha deliberadamente variables peatonales para SITP y confina el ruteo a estaciones bajo techo del circuito rojo de Transmilenio como medida paliativa de seguridad urbana nocturna.

Para una exploración intensa de cómo funcionan estos diagramas, revisa [ARQUITECTURA.md](ARQUITECTURA.md).

## Requisitos

- **Docker** y **Docker Compose**
- **Ollama** instalado en la máquina central corriendo el modelo `llama3.2`.
- Un **Telegram Bot Token** fresco adquirido a través de `@BotFather`.
- Un **Google Maps API Key** configurado para "Directions API".

## Despliegue en 3 Pasos

### 1. Configurar Entorno
Clona este repositorio y asienta el token ambiental local:
```bash
cp .env.example .env
```
Sobrescribe en `.env` tus token llaves nativas.

### 2. Levantar Motor de Lenguaje Local
Asegúrate de que tu PC o Mac cuente con Ollama corriendo bajo fondo:
```bash
ollama serve
ollama pull llama3.2
```

### 3. Container Start
Ejecuta la virtualización:
```bash
docker compose up --build -d
```
¡Tu Bot bogotano está armado y escaneando su feed en la Nube oficial de Telegram!


## Panel Comandos

| Comando | Acción |
|---------|-------------|
| `/start` | Manual de Bienvenida |
| `/status` | Estado del Sistema Inteligente (LLM + Maps) |
| `/routes` | Guía de estaciones organizadas por Troncales rojas |
| `/bloqueo` | Permite bloquear temporal e inmediatamente una estación manual por un usuario alertante (TTL 2h) |

### Casos de Uso Naturales

No necesitas memorizar sintaxis; dirígete a él como a un ciudadano de a pie (gracias a Ollama):
```
De Ricaurte a Portal Norte
Necesito ir mañana en la tarde al Centro Histórico
```

## Privacidad Legal
Este artefacto delega el análisis sintáctico al nodo nativo (Ollama). Por ello, tu ruta no viaja a EE.UU bajo un prompt de GPT/OpenAI de terceros perjudicial, brindando anonimato extremo al consumidor final de este modelo en redes telemáticas locales.
