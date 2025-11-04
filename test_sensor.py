#!/usr/bin/env python3
"""
TDS Sensor Simulator
Simulates a TDS sensor sending readings to the Flask application.
Use this to test the application without physical hardware.
"""

import requests
import time
import random
import sys

# Configuration
API_URL = "http://localhost:5000/ingest"
API_KEY = "flaskapp-tdsvalue"
DEVICE_ID = "device-1"

# Simulate different water quality scenarios
SCENARIOS = {
    "excellent": (50, 150),      # TDS range 50-150 ppm
    "good": (150, 300),          # TDS range 150-300 ppm
    "fair": (300, 500),          # TDS range 300-500 ppm
    "poor": (500, 800),          # TDS range 500-800 ppm
}

def send_reading(tds, voltage=3.3, raw=1024):
    """Send a single reading to the Flask app"""
    headers = {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    }
    data = {
        "device_id": DEVICE_ID,
        "tds": round(tds, 2),
        "voltage": round(voltage, 3),
        "raw": raw
    }
    
    try:
        response = requests.post(API_URL, json=data, headers=headers)
        if response.status_code == 200:
            result = response.json()
            print(f"✓ Sent: TDS={tds:.1f} ppm | Avg={result.get('avg_tds_ppm', 'N/A')} | Count={result.get('window_count', 0)}")
            return True
        else:
            print(f"✗ Error: {response.status_code} - {response.text}")
            return False
    except requests.exceptions.ConnectionError:
        print("✗ Connection Error: Is the Flask app running at", API_URL, "?")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def simulate_readings(scenario="excellent", count=15, interval=1.0):
    """Simulate multiple TDS readings"""
    if scenario not in SCENARIOS:
        print(f"Invalid scenario. Choose from: {', '.join(SCENARIOS.keys())}")
        return
    
    min_tds, max_tds = SCENARIOS[scenario]
    print(f"\n🌊 Simulating {scenario.upper()} water quality")
    print(f"📊 TDS Range: {min_tds}-{max_tds} ppm")
    print(f"📡 Sending {count} readings (1 every {interval}s)")
    print(f"🎯 Target: {API_URL}")
    print("-" * 60)
    
    for i in range(count):
        # Generate realistic TDS value with slight variance
        base_tds = random.uniform(min_tds, max_tds)
        tds = base_tds + random.uniform(-10, 10)  # Add noise
        
        # Generate corresponding voltage (TDS sensors typically output 0-5V)
        voltage = 3.3 + random.uniform(-0.2, 0.2)
        
        # Generate raw ADC value
        raw = int(1024 * (voltage / 5.0))
        
        print(f"[{i+1}/{count}] ", end="")
        success = send_reading(tds, voltage, raw)
        
        if not success:
            print("\n⚠ Stopping due to error")
            break
        
        if i < count - 1:  # Don't sleep after last reading
            time.sleep(interval)
    
    print("-" * 60)
    print(f"✅ Simulation complete! Check the dashboard at http://localhost:5000")

def continuous_mode(scenario="excellent", interval=1.0):
    """Continuously send readings (press Ctrl+C to stop)"""
    if scenario not in SCENARIOS:
        print(f"Invalid scenario. Choose from: {', '.join(SCENARIOS.keys())}")
        return
    
    min_tds, max_tds = SCENARIOS[scenario]
    print(f"\n🌊 Continuous {scenario.upper()} water quality monitoring")
    print(f"📊 TDS Range: {min_tds}-{max_tds} ppm")
    print(f"⏱️  Interval: {interval}s")
    print(f"🎯 Target: {API_URL}")
    print("Press Ctrl+C to stop")
    print("-" * 60)
    
    count = 0
    try:
        while True:
            count += 1
            base_tds = random.uniform(min_tds, max_tds)
            tds = base_tds + random.uniform(-10, 10)
            voltage = 3.3 + random.uniform(-0.2, 0.2)
            raw = int(1024 * (voltage / 5.0))
            
            print(f"[{count}] ", end="")
            send_reading(tds, voltage, raw)
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n" + "-" * 60)
        print(f"✅ Stopped after {count} readings")

def print_usage():
    """Print usage instructions"""
    print("""
TDS Sensor Simulator
====================

Usage:
    python test_sensor.py [scenario] [count] [interval]
    python test_sensor.py continuous [scenario] [interval]

Scenarios:
    excellent - TDS 50-150 ppm (ideal drinking water)
    good      - TDS 150-300 ppm (acceptable)
    fair      - TDS 300-500 ppm (drinkable)
    poor      - TDS 500-800 ppm (not recommended)

Examples:
    python test_sensor.py excellent 15 1.0    # Send 15 readings, 1 second apart
    python test_sensor.py good 20 0.5         # Send 20 readings, 0.5s apart
    python test_sensor.py continuous excellent 1.0  # Continuous mode
    
Default: excellent quality, 15 readings, 1 second interval
""")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ["-h", "--help", "help"]:
        print_usage()
        sys.exit(0)
    
    # Parse arguments
    if len(sys.argv) > 1 and sys.argv[1] == "continuous":
        scenario = sys.argv[2] if len(sys.argv) > 2 else "excellent"
        interval = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0
        continuous_mode(scenario, interval)
    else:
        scenario = sys.argv[1] if len(sys.argv) > 1 else "excellent"
        count = int(sys.argv[2]) if len(sys.argv) > 2 else 15
        interval = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0
        simulate_readings(scenario, count, interval)
