// ==========================================
// Sistema Vision — Arduino UNO
// ==========================================
// Motor NEMA 17 + A4988
//   STEP -> Pin 3
//   DIR  -> Pin 2
//
// Botones (Pull-Up: 1K a 3.3V, botón a GND)
//   INICIAR -> Pin 5 (LOW = presionado)
//   DETENER -> Pin 6 (LOW = presionado)
//
// Servo clasificador
//   SIGNAL -> Pin 9
//
// Comandos Serial (desde servidor):
//   START      -> Iniciar motor
//   STOP       -> Detener motor
//   VEL:xx     -> Velocidad (0-100)
//   SERVO:0    -> Tornillo
//   SERVO:1    -> Tuerca
//   SERVO:2    -> Objeto extraño
//   STATUS     -> Reportar estado
// ==========================================

#include <Servo.h>

// ═══════════════════════════════════════════
//  AJUSTES FÁCILES DE EDITAR
// ═══════════════════════════════════════════

// ─── Pines ───────────────────────────────
#define STEP_PIN    3
#define DIR_PIN     2
#define BTN_START   5
#define BTN_STOP    6
#define SERVO_PIN   9

// ─── Grados del servo (AJUSTAR AQUÍ) ────
#define SERVO_TORNILLO   30    // Posición para tornillo
#define SERVO_TUERCA     90    // Posición para tuerca
#define SERVO_EXTRANO   150    // Posición para objeto extraño
#define SERVO_NEUTRO     90    // Posición de reposo

// ─── Velocidad del motor ─────────────────
unsigned long stepDelayUs = 1200;  // Menor = más rápido

// ═══════════════════════════════════════════

Servo servoClasif;

bool motorActivo = false;
int velocidadPct = 50;

// Debounce
bool lastStart = HIGH;
bool lastStop = HIGH;
unsigned long lastDebounceStart = 0;
unsigned long lastDebounceStop = 0;
const unsigned long DEBOUNCE = 250;

// Serial
String serialBuffer = "";

void setup() {
  // Motor
  pinMode(STEP_PIN, OUTPUT);
  pinMode(DIR_PIN, OUTPUT);
  digitalWrite(DIR_PIN, HIGH);

  // Botones Pull-Up externo (1K a 3.3V, botón a GND)
  // Cuando NO se presiona: HIGH (3.3V por resistencia)
  // Cuando se presiona: LOW (conectado a GND)
  pinMode(BTN_START, INPUT);
  pinMode(BTN_STOP, INPUT);

  // Servo
  servoClasif.attach(SERVO_PIN);
  servoClasif.write(SERVO_NEUTRO);

  Serial.begin(9600);
  Serial.println("VISION:READY");
  delay(500);
}

void loop() {
  leerBotones();
  leerSerial();

  if (motorActivo) {
    digitalWrite(STEP_PIN, HIGH);
    delayMicroseconds(stepDelayUs);
    digitalWrite(STEP_PIN, LOW);
    delayMicroseconds(stepDelayUs);
  }
}

// ─── Botones con Pull-Up (LOW = presionado) ─────
void leerBotones() {
  unsigned long ahora = millis();
  bool btnStart = digitalRead(BTN_START);
  bool btnStop = digitalRead(BTN_STOP);

  // Botón INICIAR: detectar flanco HIGH -> LOW
  if (btnStart == LOW && lastStart == HIGH && (ahora - lastDebounceStart > DEBOUNCE)) {
    if (!motorActivo) {
      motorActivo = true;
      Serial.println("VISION:STARTED:BTN");
    }
    lastDebounceStart = ahora;
  }
  lastStart = btnStart;

  // Botón DETENER: detectar flanco HIGH -> LOW
  if (btnStop == LOW && lastStop == HIGH && (ahora - lastDebounceStop > DEBOUNCE)) {
    if (motorActivo) {
      motorActivo = false;
      digitalWrite(STEP_PIN, LOW);
      servoClasif.write(SERVO_NEUTRO);
      Serial.println("VISION:STOPPED:BTN");
    }
    lastDebounceStop = ahora;
  }
  lastStop = btnStop;
}

// ─── Comandos serial desde el servidor ───────────
void leerSerial() {
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') {
      if (serialBuffer.length() > 0) {
        procesarComando(serialBuffer);
        serialBuffer = "";
      }
    } else {
      serialBuffer += c;
    }
  }
}

void procesarComando(String cmd) {
  cmd.trim();
  cmd.toUpperCase();

  if (cmd == "START") {
    motorActivo = true;
    Serial.println("VISION:STARTED:SERIAL");

  } else if (cmd == "STOP") {
    motorActivo = false;
    digitalWrite(STEP_PIN, LOW);
    servoClasif.write(SERVO_NEUTRO);
    Serial.println("VISION:STOPPED:SERIAL");

  } else if (cmd.startsWith("VEL:")) {
    int vel = cmd.substring(4).toInt();
    vel = constrain(vel, 0, 100);
    velocidadPct = vel;
    stepDelayUs = map(vel, 0, 100, 2000, 400);
    Serial.print("VISION:VEL:");
    Serial.println(vel);

  } else if (cmd.startsWith("SERVO:")) {
    int clase = cmd.substring(6).toInt();
    moverServo(clase);

  } else if (cmd == "STATUS") {
    Serial.print("VISION:STATUS:");
    Serial.print(motorActivo ? "ON" : "OFF");
    Serial.print(":VEL:");
    Serial.print(velocidadPct);
    Serial.print(":SERVO:");
    Serial.println(servoClasif.read());

  } else {
    Serial.print("VISION:UNKNOWN:");
    Serial.println(cmd);
  }
}

// ─── Servo clasificador ──────────────────────────
void moverServo(int clase) {
  int pos;
  switch (clase) {
    case 0:
      pos = SERVO_TORNILLO;
      Serial.println("VISION:SERVO:TORNILLO");
      break;
    case 1:
      pos = SERVO_TUERCA;
      Serial.println("VISION:SERVO:TUERCA");
      break;
    case -1:
    case 2:
      pos = SERVO_EXTRANO;
      Serial.println("VISION:SERVO:EXTRANO");
      break;
    default:
      pos = SERVO_NEUTRO;
      Serial.println("VISION:SERVO:NEUTRO");
      break;
  }
  servoClasif.write(pos);
}
