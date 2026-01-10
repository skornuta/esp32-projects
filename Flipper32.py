import network
import bluetooth
import time
import random
import json
from machine import I2C, Pin, ADC, PWM
from pico_i2c_lcd import I2cLcd

# --- 1. HARDWARE SETUP ---
i2c = I2C(0, sda=Pin(21), scl=Pin(22), freq=400000)
lcd = I2cLcd(i2c, i2c.scan()[0], 2, 16)
joy_y = ADC(Pin(35))
joy_y.atten(ADC.ATTN_11DB)
joy_x = ADC(Pin(34))          # Assuming X-axis on GPIO34 - change if different
joy_x.atten(ADC.ATTN_11DB)    # Full range 0-4095
joy_btn = Pin(12, Pin.IN, Pin.PULL_UP)

# IR & Alarm Hardware
ir_tx = Pin(4, Pin.OUT)
ir_rx = Pin(15, Pin.IN)
pir = Pin(13, Pin.IN)
buzzer = PWM(Pin(18))
buzzer.duty(0)

def beep(freq=1000, duration=0.1):
    buzzer.freq(freq)
    buzzer.duty(512)
    time.sleep(duration)
    buzzer.duty(0)
    
def check_back():
    # If X-axis is tilted left (usually < 500)
    if joy_x.read() < 500:
        beep(600, 0.1)
        return True
    return False
# --- 2. BOOT SEQUENCE ---
def boot_sequence():
    lcd.clear()
    lcd.putstr(" Flipper32 \n")
    lcd.putstr(" v1.1.2 ")
   
    startup_notes = [523, 659, 784]
    for note in startup_notes:
        beep(note, 0.15)
        time.sleep(0.05)
   
    time.sleep(0.5)
    lcd.clear()
    lcd.putstr("Initializing...")
   
    for i in range(16):
        lcd.move_to(i, 1)
        lcd.putstr(".")
        time.sleep(0.05)
   
    beep(1046, 0.1)
    time.sleep(0.5)

# --- 3. THE "APP" FUNCTIONS ---
def run_wifi_scanner():
    lcd.clear()
    lcd.putstr("WiFi Sniffing...")
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    nets = wlan.scan()
    nets.sort(key=lambda x: x[3], reverse=True)
   
    for n in nets[:5]:
        ssid = n[0].decode('utf-8') or "Hidden"
        lcd.clear()
        lcd.putstr(f"SSID: {ssid[:10]}\nRSSI: {n[3]}")
        beep(2000, 0.05)
        time.sleep(1.5)
   
    wlan.active(False)
    lcd.clear()
    lcd.putstr("Scan Done!")
    time.sleep(1)

def run_bt_scanner():
    lcd.clear()
    lcd.putstr("BT Sniffing...")
    ble = bluetooth.BLE()
    ble.active(True)
    time.sleep(2)
    lcd.clear()
    lcd.putstr("BT Finished")
    time.sleep(1)
    ble.active(False)

# Add these at the top (near other imports)
import random  # for random data

# ... (keep your existing code up to run_ble_spam)

def run_ble_spam():
    spam_types = ["Test iBeacon", "AirPods Try", "Random BLE"]
    sub_selection = 0
    sub_running = True
    
    # Show sub-menu
    def draw_sub_menu():
        lcd.clear()
        lcd.move_to(0, 0)
        lcd.putstr("> " + spam_types[sub_selection][:13])  # truncate if too long
        lcd.move_to(0, 1)
        if sub_selection + 1 < len(spam_types):
            lcd.putstr(" " + spam_types[sub_selection + 1][:13])
        # Indicators
        if sub_selection > 0:
            lcd.move_to(15, 0)
            lcd.putstr("^")
        if sub_selection < len(spam_types) - 1:
            lcd.move_to(15, 1)
            lcd.putstr("v")    
    draw_sub_menu()
    
    ble = bluetooth.BLE()
    ble.active(True)
    
    try:
        while sub_running:
            # CHECK FOR EXIT FIRST
            if check_back():
                sub_running = False # This will exit the sub-menu
                break
            
            # Joystick up/down navigation
            if y_val > 3500 and sub_selection < len(spam_types) - 1:
                sub_selection += 1
                beep(800, 0.05)
                draw_sub_menu()
                time.sleep(0.3)
            if y_val < 500 and sub_selection > 0:
                sub_selection -= 1
                beep(1200, 0.05)
                draw_sub_menu()
                time.sleep(0.3)
            
            # Button press = select & start spam
            if joy_btn.value() == 0:
                time.sleep(0.1)
                if joy_btn.value() == 0:  # debounce
                    beep(1500, 0.1)
                    lcd.clear()
                    lcd.putstr("Starting:\n" + spam_types[sub_selection][:13])
                    time.sleep(1)
                    
                    # Choose payload based on selection
                    if sub_selection == 0:  # Test iBeacon (reliable in scanners)
                        payload = bytes([0x02, 0x01, 0x06, 0x1A, 0xFF, 0x4C, 0x00, 0x02, 0x15]) + \
                                  b'\xE2\x0A\x39\xF4\x73\xF5\x4B\xC4\xA1\x2F\x17\xD1\xAD\x07\xA9\x61' + \
                                  b'\x00\x01\x00\x02' + bytes([0xC5])  # 30 bytes
                    elif sub_selection == 1:  # AirPods proximity attempt (short version)
                        payload = bytes([0x1E, 0xFF, 0x4C, 0x00, 0x12, 0x19, 0x18])  # 7 bytes - minimal
                    else:  # Random/general BLE (fun mix)
                        payload = bytes([0x02, 0x01, 0x06, 0x09, 0x09]) + b"Flipper" + bytes([random.randint(0,255) for _ in range(8)])
                    
                    # Run spam loop (30s or button exit)
                    start = time.time()
                    while time.time() - start < 30:
                        ble.gap_advertise(200000, adv_data=payload, connectable=False)
                        time.sleep(0.3)
                        if joy_btn.value() == 0:  # exit spam
                            time.sleep(0.2)
                            break
                    
                    lcd.clear()
                    lcd.putstr("Spam Done")
                    time.sleep(1)
                    draw_sub_menu()  # back to sub-menu
            
            # Long-press button (~1s) to exit sub-menu
            if joy_btn.value() == 0:
                press_start = time.time()
                while joy_btn.value() == 0:
                    if time.time() - press_start > 1:
                        sub_running = False
                        beep(2000, 0.2)
                        break
            
            time.sleep(0.1)
    
    finally:
        ble.active(False)
        lcd.clear()
        lcd.putstr("BLE Spam Exit")
        time.sleep(1)

# Funny SSID list - add/edit as many as you want!
import random  # add at top if not there

funny_ssids = [
    "FBI Van #420",
    "Virus.exe Downloading",
    "Mom Use This One",
    "LAN Solo",
    "Pretty Fly for a WiFi",
    "Bill Wi the Science Fi",
    "Free Public WiFi (Scam)",
    "Get Off My LAN",
    "Abraham Linksys",
    "Silence of the LANs",
    "404 WiFi Not Found",
    "Hide Yo Kids Hide Yo WiFi"
]  # shorter & funnier — feel free to edit

def run_wifi_spammer():
    lcd.clear()
    lcd.putstr("WiFi Spam Active")
    lcd.move_to(0,1)
    lcd.putstr("Cycling funny SSIDs")

    wlan = network.WLAN(network.AP_IF)
    wlan.active(True)

    try:
        start = time.time()
        i = 0
        while time.time() - start < 60:  # 1 min
            if check_back(): break
            ssid = random.choice(funny_ssids)  # random instead of sequential
            channel = random.randint(1, 11)    # random channel 1-11

            try:
                wlan.config(essid=ssid, channel=channel)  # set channel too!
                print(f"Broadcasting: {ssid} on ch{channel}")
                beep(1800 + i*50, 0.1)  # rising pitch for fun
            except Exception as e:
                print("Config error:", e)

            i += 1
            time.sleep(1.2)  # slower: ~0.8/sec — more likely to be seen

            if joy_btn.value() == 0:  # hold to exit
                time.sleep(0.3)
                if joy_btn.value() == 0:
                    break
    finally:
        wlan.active(False)

    lcd.clear()
    lcd.putstr("Spam Stopped")
    time.sleep(1)
    
    
import json # Add this to the very top of your main.py

# --- GLOBAL STORAGE ---
captured_list = []

# Load codes from memory on startup
try:
    with open('ir_data.json', 'r') as f:
        captured_list = json.load(f)
except:
    captured_list = []

def save_codes():
    with open('ir_data.json', 'w') as f:
        json.dump(captured_list, f)

def run_ir_cloner():
    global captured_list
    sub_selection = 0
    needs_update = True

    while True:
        # 1. EXIT (Left)
        if check_back(): break

        # 2. DELETE (Right) - Only if we aren't hovering over "Scan New"
        if joy_x.read() > 3500 and sub_selection > 0:
            beep(400, 0.1)
            captured_list.pop(sub_selection - 1) # -1 because list starts after "Scan"
            save_codes()
            needs_update = True
            time.sleep(0.3)

        # 3. NAVIGATION (Up/Down)
        y_val = joy_y.read()
        # Max selection is len of list + 1 (for the Scan option)
        if y_val > 3500 and sub_selection < len(captured_list):
            sub_selection += 1
            beep(800, 0.05); needs_update = True; time.sleep(0.2)
        elif y_val < 500 and sub_selection > 0:
            sub_selection -= 1
            beep(1200, 0.05); needs_update = True; time.sleep(0.2)

        # 4. REDRAW
        if needs_update:
            lcd.clear()
            if sub_selection == 0:
                lcd.putstr("> [SCAN NEW CODE]")
                if len(captured_list) > 0:
                    lcd.move_to(0, 1)
                    lcd.putstr(f"  Code 1")
            else:
                lcd.putstr(f"> Code {sub_selection}")
                lcd.move_to(0, 1)
                # Show the NEXT code in the list if it exists
                if sub_selection < len(captured_list):
                    lcd.putstr(f"  Code {sub_selection + 1}")
                else:
                    lcd.putstr("  [End of List]")
            
            # Arrows
            if sub_selection > 0: lcd.move_to(15, 0); lcd.putstr("^")
            if sub_selection < len(captured_list): lcd.move_to(15, 1); lcd.putstr("v")
            needs_update = False

        # 5. ACTION (Click)
        if joy_btn.value() == 0:
            time.sleep(0.2)
            if sub_selection == 0:
                # --- SCANNING ---
                lcd.clear()
                lcd.putstr("LISTENING...")
                raw = []
                while ir_rx.value() == 1:
                    if check_back(): break
                if ir_rx.value() == 0:
                    start = time.ticks_us()
                    while time.ticks_diff(time.ticks_us(), start) < 150000:
                        p_start = time.ticks_us()
                        val = ir_rx.value()
                        while ir_rx.value() == val and time.ticks_diff(time.ticks_us(), p_start) < 50000:
                            pass
                        raw.append(time.ticks_diff(time.ticks_us(), p_start))
                    if len(raw) > 5:
                        captured_list.append(raw)
                        save_codes()
                        beep(2000, 0.1)
                        lcd.clear(); lcd.putstr("SAVED AS"); lcd.move_to(0,1); lcd.putstr(f"Code {len(captured_list)}")
                        time.sleep(1)
                needs_update = True
            else:
                # --- BLASTING ---
                lcd.move_to(0, 1)
                lcd.putstr(">> BLASTING! << ")
                this_code = captured_list[sub_selection - 1]
                for i, dur in enumerate(this_code):
                    ir_tx.value(1 if i % 2 == 0 else 0)
                    time.sleep_us(dur)
                ir_tx.value(0)
                time.sleep(0.3)
                needs_update = True
        
        time.sleep(0.05)

# --- 4. MENU SETTINGS ---
apps = ["WiFi Sniffer", "BT Sniffer", "BLE Spammer", "WIFI Spammer", "IR Cloner"]
current_selection = 0

def draw_menu():
    lcd.clear()
   
    # Line 1: Current Selection
    lcd.move_to(0, 0)
    lcd.putstr("> " + apps[current_selection])
   
    # Line 2: Next Preview
    lcd.move_to(0, 1)
    if current_selection + 1 < len(apps):
        lcd.putstr(" " + apps[current_selection + 1])
    # --- Right Side Scroll Indicators ---
    if current_selection > 0:
        lcd.move_to(15, 0)
        lcd.putstr("^")
       
    if current_selection < len(apps) - 1:
        lcd.move_to(15, 1)
        lcd.putstr("v")

# --- 5. EXECUTION ---
# --- 5. EXECUTION ---
boot_sequence()
draw_menu()

while True:
    y_val = joy_y.read()
    x_val = joy_x.read() 
    
    # 1. PRIORITY: Vertical Navigation (Up/Down)
    if y_val > 3500: # Down
        if current_selection < len(apps) - 1:
            current_selection += 1
            beep(800, 0.05)
            draw_menu()
            time.sleep(0.3)
            
    elif y_val < 500: # Up
        if current_selection > 0:
            current_selection -= 1
            beep(1200, 0.05)
            draw_menu()
            time.sleep(0.3)

    # 2. SECONDARY: Horizontal Shortcuts (Left/Right)
    # Using 'elif' here prevents these from triggering if you are moving Up/Down
    elif x_val < 500: # LEFT: Reset Home
        if current_selection != 0:
            beep(2000, 0.05)
            current_selection = 0
            lcd.clear()
            lcd.putstr("Returning Home..")
            time.sleep(0.3)
            draw_menu()

    elif x_val > 3500: # RIGHT: Version Info
        lcd.move_to(0,0)
        lcd.putstr("Flipper32 v1.1.2")
        time.sleep(0.5)
        draw_menu()

    # 3. SELECTION (Click)
    if joy_btn.value() == 0:
        time.sleep(0.05)
        if joy_btn.value() == 0:
            beep(1500, 0.1)
            lcd.clear()
            lcd.putstr("Launching:\n" + apps[current_selection])
            while joy_btn.value() == 0: time.sleep(0.01)
            time.sleep(0.2)
            
            if current_selection == 0: run_wifi_scanner()
            elif current_selection == 1: run_bt_scanner()
            elif current_selection == 2: run_ble_spam()
            elif current_selection == 3: run_wifi_spammer()
            elif current_selection == 4: run_ir_cloner()
            
            draw_menu()

    time.sleep(0.1)
