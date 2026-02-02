# Blinking LED Strip Using ESP32

## Goal
Build a device that controls a WS2812B LED strip using an ESP32, demonstrating how to turn LEDs on and off and change their colors using the FastLED library.

## Language: C

## Hardware
- ESP32 development board  
- WS2812B (NeoPixel-compatible) LED strip (8 LEDs)  
- Jumper wires  
- 5V power source (or ESP32 5V pin, depending on strip)

## Software
- PlatformIO (VS Code extension)  
- Arduino framework for ESP32  
- FastLED library  

## Photos
![LED Strip Tricks](led-tricks.png)

## How to Run

### 1. Install PlatformIO
- Open **VS Code**
- Install the **PlatformIO IDE** extension

### 2. Create a New Project
- Open PlatformIO → **New Project**
- Select your ESP32 board (e.g. `esp32dev`)
- Choose **Arduino** as the framework

### 3. Install FastLED
Open `platformio.ini` and add:
```ini
lib_deps =
  fastled/FastLED
```

### 4. Add the Code

Open src/main.cpp

Paste in the LED blinking code

### 5. Wire the Hardware

LED strip DIN → ESP32 GPIO 2

LED strip 5V → ESP32 5V

LED strip GND → ESP32 GND

### 6. Upload and Run

Connect the ESP32 to your computer via USB

Click Upload in PlatformIO

The first LED will blink red and blue every 0.5 seconds