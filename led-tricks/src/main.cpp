#include <FastLED.h>

#define LED_PIN     2    // Make sure your wire is on D2
#define NUM_LEDS    8    
#define COLOR_ORDER GRB  // If Red and Green are swapped later, change this to RGB

// THIS IS THE LINE THAT WAS MISSING:
CRGB leds[NUM_LEDS];

void setup() {
    // This tells the library which pin and how many LEDs you have
    FastLED.addLeds<WS2812B, LED_PIN, COLOR_ORDER>(leds, NUM_LEDS);
    FastLED.setBrightness(50);
    
    // Clear the strip on startup
    FastLED.clear();
    FastLED.show();
}

void loop() {
    // Light up the first LED Red
    leds[0] = CRGB::Red;
    FastLED.show();
    delay(500);

    // Light up the first LED Blue
    leds[0] = CRGB::Blue;
    FastLED.show();
    delay(500);
}