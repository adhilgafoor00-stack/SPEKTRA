// SPEKTRA board firmware: Arduino Uno/Nano or ESP32 (Arduino core).
// Wiring (change the pins below to match your board):
//   LED       -> LED_PIN (built-in LED works)
//   LDR       -> LIGHT_PIN through a voltage divider
//   DHT11/22  -> DHT_PIN (needs the "DHT sensor library" by Adafruit)
//
// Protocol (115200 baud, newline-terminated): see core/hardware.py
#include <DHT.h>

#define LED_PIN   LED_BUILTIN
#define LIGHT_PIN A0
#define DHT_PIN   2
#define DHT_TYPE  DHT11

DHT dht(DHT_PIN, DHT_TYPE);

void setup() {
  Serial.begin(115200);
  pinMode(LED_PIN, OUTPUT);
  dht.begin();
}

void loop() {
  if (!Serial.available()) return;
  String cmd = Serial.readStringUntil('\n');
  cmd.trim();
  cmd.toUpperCase();

  if (cmd == "PING") {
    Serial.println("PONG");
  } else if (cmd == "GET TEMP") {
    float t = dht.readTemperature();
    Serial.println(isnan(t) ? "ERR" : String(t, 1));
  } else if (cmd == "GET HUM") {
    float h = dht.readHumidity();
    Serial.println(isnan(h) ? "ERR" : String(h, 1));
  } else if (cmd == "GET LIGHT") {
    Serial.println(analogRead(LIGHT_PIN));
  } else if (cmd == "LED ON") {
    digitalWrite(LED_PIN, HIGH);
    Serial.println("OK");
  } else if (cmd == "LED OFF") {
    digitalWrite(LED_PIN, LOW);
    Serial.println("OK");
  } else {
    Serial.println("ERR");
  }
}
