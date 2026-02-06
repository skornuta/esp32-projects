#include <Arduino.h>
#include <Wire.h>

// ----- Feature flags -----
#define ENABLE_LCD 1
#define ENABLE_IR 1
#define ENABLE_CC1101 1
#define ENABLE_SERIAL_LOG 1

// ----- Pin map (wire later) -----
// Buttons (active LOW, use internal pullups)
#define BTN_UP_PIN 33
#define BTN_DOWN_PIN 25
#define BTN_SELECT_PIN 26
#define BTN_BACK_PIN 27

// I2C (LCD 1602)
#define I2C_SDA_PIN 21
#define I2C_SCL_PIN 22
#define LCD_ADDR 0x27

// Change IR to a safe input-only pin
#define IR_RX_PIN 34 

// Standard VSPI Pinout for CC1101
#define CC1101_SCK 18
#define CC1101_MISO 19   // Changed from 36
#define CC1101_MOSI 23
#define CC1101_CSN 5
#define CC1101_GDO0 4
#define CC1101_GDO2 15
#define CC1101_RST -1

// ----- Optional libs (compile if available) -----
#if __has_include(<LiquidCrystal_I2C.h>)
  #include <LiquidCrystal_I2C.h>
  #define HAS_LCD_LIB 1
#else
  #define HAS_LCD_LIB 0
#endif

#if __has_include(<IRremoteESP8266.h>)
  #include <IRremoteESP8266.h>
  #include <IRrecv.h>
  #include <IRutils.h>
  #define HAS_IR_LIB 1
#else
  #define HAS_IR_LIB 0
#endif

#if __has_include(<RadioLib.h>)
  #include <RadioLib.h>
  #define HAS_CC1101_LIB 1
  #define HAS_RADIOLIB 1
#elif __has_include(<ELECHOUSE_CC1101_SRC_DRV.h>)
  #include <ELECHOUSE_CC1101_SRC_DRV.h>
  #define HAS_CC1101_LIB 1
  #define HAS_RADIOLIB 0
#else
  #define HAS_CC1101_LIB 0
  #define HAS_RADIOLIB 0
#endif

// ----- Globals -----
#if ENABLE_LCD && HAS_LCD_LIB
LiquidCrystal_I2C lcd(LCD_ADDR, 16, 2);
#endif

// ----- Simple button handling -----
struct Button {
  uint8_t pin;
  bool state;
  bool last_state;
  uint32_t last_change_ms;

  void begin() {
    pinMode(pin, INPUT_PULLUP);
    state = readRaw();
    last_state = state;
    last_change_ms = millis();
  }

  bool readRaw() const {
    return digitalRead(pin) == LOW; // active LOW
  }

  bool fell() {
    bool raw = readRaw();
    uint32_t now = millis();
    if (raw != last_state && (now - last_change_ms) > 25) {
      last_state = raw;
      last_change_ms = now;
      if (raw && !state) {
        state = raw;
        return true;
      }
      state = raw;
    }
    return false;
  }
};

Button btnUp { BTN_UP_PIN, false, false, 0 };
Button btnDown { BTN_DOWN_PIN, false, false, 0 };
Button btnSelect { BTN_SELECT_PIN, false, false, 0 };
Button btnBack { BTN_BACK_PIN, false, false, 0 };

// ----- UI state -----
enum UiMode { MODE_MENU, MODE_APP };
UiMode uiMode = MODE_MENU;

enum AppId { APP_IR, APP_SUBGHZ, APP_UTILS, APP_SETTINGS };

struct MenuItem {
  const char* name;
  AppId app;
};

const MenuItem menuItems[] = {
  { "IR Tools", APP_IR },
  { "Sub-GHz", APP_SUBGHZ },
  { "Utilities", APP_UTILS },
  { "Settings", APP_SETTINGS },
};

const uint8_t MENU_COUNT = sizeof(menuItems) / sizeof(menuItems[0]);
uint8_t menuIndex = 0;

// ----- LCD helpers -----
void lcdClearLine(uint8_t line) {
#if ENABLE_LCD && HAS_LCD_LIB
  lcd.setCursor(0, line);
  for (uint8_t i = 0; i < 16; i++) lcd.print(' ');
  lcd.setCursor(0, line);
#else
  (void)line;
#endif
}

void lcdPrintLine(uint8_t line, const String& text) {
#if ENABLE_LCD && HAS_LCD_LIB
  lcdClearLine(line);
  lcd.print(text.substring(0, 16));
#else
  Serial.println(text);
  (void)line;
#endif
}

void showMenu() {
  uint8_t top = (menuIndex / 2) * 2;
  String line0 = String((menuIndex == top) ? "> " : "  ") + menuItems[top].name;
  String line1 = "";
  if (top + 1 < MENU_COUNT) {
    line1 = String((menuIndex == top + 1) ? "> " : "  ") + menuItems[top + 1].name;
  }
  lcdPrintLine(0, line0);
  lcdPrintLine(1, line1);
}

// ----- App state -----
AppId activeApp = APP_IR;

// IR app
uint32_t irCount = 0;
uint32_t irLastCode = 0;
uint32_t irLastAtMs = 0;

#if ENABLE_IR && HAS_IR_LIB
IRrecv irrecv(IR_RX_PIN);
decode_results irResults;
#endif

void appIrBegin() {
  irCount = 0;
  irLastCode = 0;
  irLastAtMs = 0;
  lcdPrintLine(0, "IR Receiver");
  lcdPrintLine(1, "Waiting...");
}

void appIrUpdate() {
#if ENABLE_IR
#if HAS_IR_LIB
  if (irrecv.decode(&irResults)) {
    irCount++;
    irLastCode = irResults.value;
    irLastAtMs = millis();
    irrecv.resume();
  }
  String line1 = String("C:") + irCount;
  if (irLastAtMs != 0) {
    line1 += " 0x";
    line1 += String(irLastCode, HEX);
  } else {
    line1 += " Waiting";
  }
  lcdPrintLine(1, line1);
#else
  lcdPrintLine(1, "IR lib missing");
#endif
#else
  lcdPrintLine(1, "IR disabled");
#endif
}

// Sub-GHz app
bool cc1101Ready = false;
float ccFreq = 433.92f;
const float ccFreqs[] = { 315.00f, 433.92f, 868.35f, 915.00f };
const uint8_t CC_FREQ_COUNT = sizeof(ccFreqs) / sizeof(ccFreqs[0]);
uint8_t ccFreqIndex = 1;
int16_t lastRssi = 0;
int ccInitState = 0;

#if ENABLE_CC1101 && HAS_CC1101_LIB && HAS_RADIOLIB
CC1101 radio = new Module(CC1101_CSN, CC1101_GDO0, CC1101_RST, CC1101_GDO2);
#endif

bool ccInit() {
#if ENABLE_CC1101 && HAS_CC1101_LIB
  cc1101Ready = false;
#if HAS_RADIOLIB
  ccInitState = radio.begin();
  if (ccInitState == RADIOLIB_ERR_NONE) {
    ccFreq = ccFreqs[ccFreqIndex];
    radio.setFrequency(ccFreq);
    radio.setBitRate(4.8f);
    radio.setRxBandwidth(58.0f);
    radio.setOutputPower(10);
    cc1101Ready = true;
    return true;
  }
  return false;
#else
  cc1101Ready = true;
  return true;
#endif
#else
  cc1101Ready = false;
  return false;
#endif
}

void appSubGhzBegin() {
  lcdPrintLine(0, "Sub-GHz");
  lcdPrintLine(1, "Init...");
  if (ccInit()) {
    lcdPrintLine(1, "Ready");
  } else {
    lcdPrintLine(1, "Init fail");
  }
}

void appSubGhzUpdate() {
  if (btnUp.fell()) {
    ccFreqIndex = (ccFreqIndex + 1) % CC_FREQ_COUNT;
    ccFreq = ccFreqs[ccFreqIndex];
#if ENABLE_CC1101 && HAS_CC1101_LIB && HAS_RADIOLIB
    if (cc1101Ready) radio.setFrequency(ccFreq);
#endif
  }
  if (btnDown.fell()) {
    if (ccFreqIndex == 0) ccFreqIndex = CC_FREQ_COUNT - 1;
    else ccFreqIndex--;
    ccFreq = ccFreqs[ccFreqIndex];
#if ENABLE_CC1101 && HAS_CC1101_LIB && HAS_RADIOLIB
    if (cc1101Ready) radio.setFrequency(ccFreq);
#endif
  }
  if (btnSelect.fell()) {
    ccInit();
  }

  String line0 = String("Sub ") + String(ccFreq, 2) + "MHz";
  lcdPrintLine(0, line0);

  if (!cc1101Ready) {
    String line1 = String("Init fail ") + String(ccInitState);
    lcdPrintLine(1, line1);
    return;
  }

  String line1 = String("Ready");
#if HAS_RADIOLIB
  lastRssi = radio.getRSSI();
  if (lastRssi != RADIOLIB_ERR_UNKNOWN) {
    line1 = String("RSSI ") + lastRssi + " dBm";
  }
#endif
  lcdPrintLine(1, line1);
}

// Utilities app
void appUtilsBegin() {
  lcdPrintLine(0, "Utilities");
}

void appUtilsUpdate() {
  uint32_t up = millis() / 1000;
  String line1 = String("Uptime ") + up + "s";
  lcdPrintLine(1, line1);
}

// Settings app
void appSettingsBegin() {
  lcdPrintLine(0, "Settings");
  lcdPrintLine(1, "Edit pin map");
}

void appSettingsUpdate() {
  // Placeholder for future settings
}

void enterApp(AppId app) {
  activeApp = app;
  uiMode = MODE_APP;
  switch (app) {
    case APP_IR: appIrBegin(); break;
    case APP_SUBGHZ: appSubGhzBegin(); break;
    case APP_UTILS: appUtilsBegin(); break;
    case APP_SETTINGS: appSettingsBegin(); break;
  }
}

void updateApp() {
  switch (activeApp) {
    case APP_IR: appIrUpdate(); break;
    case APP_SUBGHZ: appSubGhzUpdate(); break;
    case APP_UTILS: appUtilsUpdate(); break;
    case APP_SETTINGS: appSettingsUpdate(); break;
  }
}

void setup() {
#if ENABLE_SERIAL_LOG
  Serial.begin(115200);
#endif

  // I2C LCD
  Wire.begin(I2C_SDA_PIN, I2C_SCL_PIN);
#if ENABLE_LCD && HAS_LCD_LIB
  lcd.init();
  lcd.backlight();
#endif

  // Buttons
  btnUp.begin();
  btnDown.begin();
  btnSelect.begin();
  btnBack.begin();

  // IR receiver
#if ENABLE_IR && HAS_IR_LIB
  irrecv.enableIRIn();
#elif ENABLE_IR
  pinMode(IR_RX_PIN, INPUT);
#endif

  // CC1101
#if ENABLE_CC1101 && HAS_CC1101_LIB
  // Placeholder: init is library-specific. Update once you pick a library.
#endif

  lcdPrintLine(0, "ESP32 Flipper");
  lcdPrintLine(1, "Booting...");
  delay(500);
  showMenu();
}

void loop() {
  if (uiMode == MODE_MENU) {
    if (btnUp.fell()) {
      if (menuIndex == 0) menuIndex = MENU_COUNT - 1;
      else menuIndex--;
      showMenu();
    }
    if (btnDown.fell()) {
      menuIndex = (menuIndex + 1) % MENU_COUNT;
      showMenu();
    }
    if (btnSelect.fell()) {
      enterApp(menuItems[menuIndex].app);
    }
  } else {
    updateApp();
    if (btnBack.fell()) {
      uiMode = MODE_MENU;
      showMenu();
    }
  }
}
