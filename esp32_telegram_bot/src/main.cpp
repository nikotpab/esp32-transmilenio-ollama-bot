#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <UniversalTelegramBot.h>
#include <NTPClient.h>
#include <WiFiUdp.h>

#include "secrets.h"

#define WIFI_RECONNECT_DELAY 5000
#define TELEGRAM_POLL_INTERVAL 1000
#define PROXY_TIMEOUT 30000

#define PROXY_SERVER_URL "http://192.168.1.100:5000"
#define ROUTE_ENDPOINT "/api/route"
#define STATUS_ENDPOINT "/api/status"

#define MAX_MESSAGE_LENGTH 4096
#define MAX_ROUTE_RETRIES 3
#define LED_PIN 2

enum SystemState {
  STATE_INIT,
  STATE_WIFI_CONNECTING,
  STATE_WIFI_CONNECTED,
  STATE_READY,
  STATE_ERROR,
  STATE_LOW_MEMORY
};

SystemState currentState = STATE_INIT;
unsigned long lastHeapCheck = 0;
unsigned long wifiConnectAttempt = 0;
uint32_t messageCount = 0;

WiFiUDP ntpUDP;
NTPClient timeClient(ntpUDP, "pool.ntp.org", -5 * 3600, 60000);

WiFiClientSecure telegramClient;
UniversalTelegramBot bot(TELEGRAM_BOT_TOKEN, telegramClient);

void setupWiFi();
void setupTelegram();
void handleTelegramMessages();
String sendToProxy(const String& message, const String& chatId);
void processRouteRequest(const String& message, const String& chatId);
void sendTelegramMessage(const String& chatId, const String& text);
void sendTelegramMessageMarkdown(const String& chatId, const String& text);
void blinkLED(int times, int delayMs);
void checkMemory();
void handleSystemState();
String getCurrentTimeBogota();
String getUptimeString();

void setup() {
  Serial.begin(115200);
  Serial.println("\n\n=== BOT TELEGRAM TRANSMILENIO/SITP ===");
  Serial.println("Iniciando sistema...");

  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);

  timeClient.begin();
  timeClient.setTimeOffset(-5 * 3600);

  currentState = STATE_WIFI_CONNECTING;
  setupWiFi();

  if (currentState == STATE_WIFI_CONNECTED) {
    setupTelegram();
    currentState = STATE_READY;
    Serial.println("Sistema listo. Esperando mensajes...");
    blinkLED(3, 200);
  } else {
    currentState = STATE_ERROR;
    Serial.println("Error: No se pudo conectar WiFi");
  }
}

void loop() {
  timeClient.update();
  handleSystemState();

  if (millis() - lastHeapCheck > 10000) {
    checkMemory();
    lastHeapCheck = millis();
  }

  if (currentState == STATE_READY) {
    handleTelegramMessages();
  }

  if (currentState == STATE_ERROR &&
      millis() - wifiConnectAttempt > WIFI_RECONNECT_DELAY) {
    Serial.println("Reintentando conexion WiFi...");
    currentState = STATE_WIFI_CONNECTING;
    setupWiFi();
  }

  delay(TELEGRAM_POLL_INTERVAL);
}

void setupWiFi() {
  Serial.print("Conectando a WiFi: ");
  Serial.println(WIFI_SSID);

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    blinkLED(1, 100);
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nWiFi conectado!");
    Serial.print("IP: ");
    Serial.println(WiFi.localIP());
    Serial.print("RSSI: ");
    Serial.print(WiFi.RSSI());
    Serial.println(" dBm");
    currentState = STATE_WIFI_CONNECTED;
  } else {
    Serial.println("\nFallo conexion WiFi");
    wifiConnectAttempt = millis();
    currentState = STATE_ERROR;
  }
}

void setupTelegram() {
  telegramClient.setInsecure();
  Serial.println("Telegram configurado");
}

void handleTelegramMessages() {
  int newMessages = bot.getUpdates(bot.lastMessageReceived + 1);

  while (newMessages) {
    for (int i = 0; i < newMessages; i++) {
      messageCount++;
      Serial.print("Mensaje #");
      Serial.print(messageCount);
      Serial.print(" de: ");
      Serial.println(bot.messages[i].chat_id);
      Serial.print("Texto: ");
      Serial.println(bot.messages[i].text);

      String text = bot.messages[i].text;

      if (text == "/start" || text == "/help") {
        handleStartCommand(bot.messages[i].chat_id);
      } else if (text == "/status") {
        handleStatusCommand(bot.messages[i].chat_id);
      } else if (text == "/routes") {
        handleRoutesCommand(bot.messages[i].chat_id);
      } else {
        processRouteRequest(text, bot.messages[i].chat_id);
      }
    }
    newMessages = bot.getUpdates(bot.lastMessageReceived + 1);
  }
}

void handleStartCommand(const String& chatId) {
  String welcome = "*Bot de Transporte Bogota*\n\n";
  welcome += "Te ayudo a encontrar la mejor ruta usando Transmilenio y SITP.\n\n";
  welcome += "*Comandos disponibles:*\n";
  welcome += "/start - Mostrar este mensaje\n";
  welcome += "/status - Estado del sistema\n";
  welcome += "/routes - Estaciones principales\n\n";
  welcome += "*Como usar:*\n";
  welcome += "Simplemente escribe tu ruta:\n";
  welcome += "```\n";
  welcome += "De Calle 100 a Portal Norte\n";
  welcome += "De Mi casa al Centro a las 8am\n";
  welcome += "```\n";
  welcome += "El bot entendera tu solicitud y te dara la mejor ruta.";

  sendTelegramMessageMarkdown(chatId, welcome);
}

void handleStatusCommand(const String& chatId) {
  String status = "*Estado del Sistema:*\n\n";
  status += "WiFi: " + String(WiFi.status() == WL_CONNECTED ? "Conectado" : "Desconectado") + "\n";
  status += "Señal: " + String(WiFi.RSSI()) + " dBm\n";
  status += "Memoria: " + String(ESP.getFreeHeap() / 1024) + " KB libres\n";
  status += "Hora Bogota: " + getCurrentTimeBogota() + "\n";
  status += "Mensajes procesados: " + String(messageCount) + "\n";
  status += "Uptime: " + getUptimeString() + "\n";

  sendTelegramMessageMarkdown(chatId, status);
}

void handleRoutesCommand(const String& chatId) {
  String routes = "*Estaciones Troncales Transmilenio:*\n\n";
  routes += "*Linea K (Norte):*\n";
  routes += "- Portal Norte\n- Calle 161\n- Calle 146\n- Calle 127\n";
  routes += "- Calle 100\n- Calle 85\n- Calle 76\n\n";
  routes += "*Linea B (Sur):*\n";
  routes += "- Portal Sur\n- Guatoque\n- General Santander\n";
  routes += "- Calle 38\n- Calle 17\n\n";
  routes += "*Linea C (Occidente):*\n";
  routes += "- Portal 80\n- Suba\n- Calle 80\n\n";
  routes += "*Linea D (Oriente):*\n";
  routes += "- Portal Eldorado\n- Aeropuerto\n\n";
  routes += "_Para rutas SITP, pregunta directamente tu origen y destino._";

  sendTelegramMessageMarkdown(chatId, routes);
}

void processRouteRequest(const String& message, const String& chatId) {
  Serial.print("Procesando solicitud de ruta: ");
  Serial.println(message);

  sendTelegramMessage(chatId, "Buscando la mejor ruta...");

  String response = sendToProxy(message, chatId);

  if (response.length() > 0) {
    StaticJsonDocument<1500> doc;
    DeserializationError error = deserializeJson(doc, response);

    if (!error) {
      String formattedResponse = formatRouteResponse(doc);
      sendTelegramMessageMarkdown(chatId, formattedResponse);
    } else {
      Serial.print("Error parsing JSON: ");
      Serial.println(error.c_str());
      sendTelegramMessage(chatId, "Error procesando la respuesta. Intenta de nuevo.");
    }
  } else {
    sendTelegramMessage(chatId, "No pude obtener informacion de la ruta. Verifica tu conexion.");
  }
}

String sendToProxy(const String& message, const String& chatId) {
  HTTPClient http;
  String response = "";

  String url = String(PROXY_SERVER_URL) + String(ROUTE_ENDPOINT);

  Serial.print("Enviando a Proxy: ");
  Serial.println(url);

  http.begin(url.c_str());
  http.addHeader("Content-Type", "application/json");
  http.setTimeout(PROXY_TIMEOUT);

  StaticJsonDocument<512> payloadDoc;
  payloadDoc["message"] = message;
  payloadDoc["chat_id"] = chatId;
  payloadDoc["timestamp"] = getCurrentTimeBogota();
  payloadDoc["location"] = "Bogota, Colombia";

  String payload;
  serializeJson(payloadDoc, payload);

  Serial.print("Payload: ");
  Serial.println(payload);

  int httpCode = http.POST(payload);

  if (httpCode > 0) {
    if (httpCode == HTTP_CODE_OK) {
      response = http.getString();
      Serial.print("Respuesta Proxy: ");
      Serial.println(response);
    } else {
      Serial.print("Error HTTP: ");
      Serial.println(httpCode);
    }
  } else {
    Serial.print("Error conexion: ");
    Serial.println(http.errorToString(httpCode));
  }

  http.end();
  return response;
}

String formatRouteResponse(const JsonDocument& doc) {
  String formatted = "";

  if (doc.containsKey("route_summary")) {
    formatted += "*Ruta Recomendada:*\n";
    formatted += doc["route_summary"].as<String>() + "\n\n";
  }

  if (doc.containsKey("steps")) {
    formatted += "*Pasos:*\n";
    JsonArray steps = doc["steps"].as<JsonArray>();
    for (size_t i = 0; i < steps.size(); i++) {
      formatted += String(i + 1) + ". " + steps[i].as<String>() + "\n";
    }
    formatted += "\n";
  }

  if (doc.containsKey("estimated_time")) {
    formatted += "Tiempo: " + doc["estimated_time"].as<String>() + "\n";
  }

  if (doc.containsKey("distance")) {
    formatted += "Distancia: " + doc["distance"].as<String>() + "\n";
  }

  if (doc.containsKey("cost")) {
    formatted += "Costo: " + doc["cost"].as<String>() + "\n";
  }

  if (doc.containsKey("recommendations")) {
    formatted += "\n*Recomendaciones:*\n";
    formatted += doc["recommendations"].as<String>() + "\n";
  }

  if (doc.containsKey("alternatives")) {
    formatted += "\n*Alternativas:*\n";
    JsonArray alternatives = doc["alternatives"].as<JsonArray>();
    for (size_t i = 0; i < alternatives.size() && i < 2; i++) {
      formatted += "- " + alternatives[i].as<String>() + "\n";
    }
  }

  return formatted;
}

void sendTelegramMessage(const String& chatId, const String& text) {
  bot.sendMessage(chatId, text, "Markdown");
}

void sendTelegramMessageMarkdown(const String& chatId, const String& text) {
  bot.sendMessage(chatId, text, "Markdown");
}

void blinkLED(int times, int delayMs) {
  for (int i = 0; i < times; i++) {
    digitalWrite(LED_PIN, HIGH);
    delay(delayMs);
    digitalWrite(LED_PIN, LOW);
    if (i < times - 1) delay(delayMs);
  }
}

void checkMemory() {
  uint32_t freeHeap = ESP.getFreeHeap();
  Serial.print("Memoria libre: ");
  Serial.print(freeHeap);
  Serial.println(" bytes");

  if (freeHeap < 50000) {
    Serial.println("ALERTA: Memoria baja!");
    currentState = STATE_LOW_MEMORY;
  } else if (freeHeap > 100000 && currentState == STATE_LOW_MEMORY) {
    currentState = STATE_READY;
  }
}

void handleSystemState() {
  switch (currentState) {
    case STATE_INIT:
      digitalWrite(LED_PIN, LOW);
      break;
    case STATE_WIFI_CONNECTING:
      digitalWrite(LED_PIN, millis() % 500 < 250 ? HIGH : LOW);
      break;
    case STATE_WIFI_CONNECTED:
      digitalWrite(LED_PIN, HIGH);
      delay(100);
      digitalWrite(LED_PIN, LOW);
      break;
    case STATE_READY:
      digitalWrite(LED_PIN, HIGH);
      break;
    case STATE_ERROR:
      digitalWrite(LED_PIN, millis() % 1000 < 500 ? HIGH : LOW);
      break;
    case STATE_LOW_MEMORY:
      digitalWrite(LED_PIN, millis() % 200 < 100 ? HIGH : LOW);
      break;
  }
}

String getCurrentTimeBogota() {
  return timeClient.getFormattedTime();
}

String getUptimeString() {
  unsigned long seconds = millis() / 1000;
  unsigned long days = seconds / 86400;
  unsigned long hours = (seconds % 86400) / 3600;
  unsigned long minutes = (seconds % 3600) / 60;

  return String(days) + "d " + String(hours) + "h " + String(minutes) + "m";
}
