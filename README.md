# 💧 WaterWatch - Smart TDS Water Quality Monitor

A modern Flask application that monitors water quality using TDS (Total Dissolved Solids) sensors with AI-powered analysis using Google Gemini.

## ✨ Features

- **Real-time TDS Monitoring** - Live readings from TDS sensors via API
- **Auto-Detection** - Automatically starts analysis when device connects
- **10-Reading Average** - Collects 10 readings and calculates average for accuracy
- **AI Analysis** - Uses Google Gemini to explain water quality in simple terms
- **Analysis History** - Stores all past analyses with timestamps
- **Modern UI** - Beautiful dark-themed dashboard with animations
- **Progress Tracking** - Visual progress indicators during data collection
- **Device Management** - Support for multiple devices

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Google Gemini API Key ([Get it here](https://makersuite.google.com/app/apikey))

### Installation

1. **Clone or download the project files**

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Set up environment variables**

Create a `.env` file or export these variables:

```bash
# Required
export GEMINI_API_KEY="your-gemini-api-key-here"

# Optional (with defaults)
export API_KEY="flaskapp-tdsvalue"  # API key for sensor authentication
export DB_PATH="./tds.db"            # Database path
```

4. **Run the application**
```bash
python app.py
```

The app will be available at `http://localhost:5000`

## 📡 How to Send Data from TDS Sensor

Your TDS sensor should send POST requests to the `/ingest` endpoint:

### Endpoint
```
POST http://your-server:5000/ingest
```

### Headers
```
X-API-Key: flaskapp-tdsvalue
Content-Type: application/json
```

### Request Body
```json
{
  "device_id": "device-1",
  "tds": 245.5,
  "voltage": 3.28,
  "raw": 1024
}
```

### Example using cURL
```bash
curl -X POST http://localhost:5000/ingest \
  -H "X-API-Key: flaskapp-tdsvalue" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "device-1",
    "tds": 245.5,
    "voltage": 3.28,
    "raw": 1024
  }'
```

### Example using Python
```python
import requests
import time

API_URL = "http://localhost:5000/ingest"
API_KEY = "flaskapp-tdsvalue"

def send_reading(tds, voltage, raw):
    headers = {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    }
    data = {
        "device_id": "device-1",
        "tds": tds,
        "voltage": voltage,
        "raw": raw
    }
    response = requests.post(API_URL, json=data, headers=headers)
    return response.json()

# Send readings every second
while True:
    # Replace with actual sensor readings
    result = send_reading(tds=250.0, voltage=3.3, raw=1024)
    print(result)
    time.sleep(1)
```

### Example using Arduino/ESP32
```cpp
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

const char* ssid = "your-wifi";
const char* password = "your-password";
const char* serverUrl = "http://your-server:5000/ingest";
const char* apiKey = "flaskapp-tdsvalue";

void sendReading(float tds, float voltage, int raw) {
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(serverUrl);
    http.addHeader("Content-Type", "application/json");
    http.addHeader("X-API-Key", apiKey);
    
    StaticJsonDocument<200> doc;
    doc["device_id"] = "device-1";
    doc["tds"] = tds;
    doc["voltage"] = voltage;
    doc["raw"] = raw;
    
    String jsonString;
    serializeJson(doc, jsonString);
    
    int httpResponseCode = http.POST(jsonString);
    
    if (httpResponseCode > 0) {
      String response = http.getString();
      Serial.println(response);
    }
    
    http.end();
  }
}

void loop() {
  // Read from TDS sensor
  float tds = readTDSSensor();
  float voltage = readVoltage();
  int raw = analogRead(TDS_PIN);
  
  sendReading(tds, voltage, raw);
  delay(1000); // Send every second
}
```

## 🔄 How It Works

### Automatic Analysis Flow

1. **Device Connects** → TDS sensor starts sending data to `/ingest` endpoint
2. **Detection** → App detects incoming readings and shows "Device Connected"
3. **Collection Phase** → App collects 10 readings (progress shown: 0/10 → 10/10)
4. **Averaging** → Calculates average TDS value from the 10 readings
5. **AI Analysis** → Sends average to Google Gemini for explanation
6. **Display Results** → Shows TDS value + AI explanation on dashboard
7. **Save to History** → Stores analysis in database with timestamp
8. **History View** → Click any past analysis in sidebar to view again

### State Machine
```
IDLE → COLLECTING (0-10 readings) → ANALYZING (AI) → COMPLETE → IDLE
```

## 📊 API Endpoints

### Public Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Main dashboard UI |
| `/healthz` | GET | Health check with stats |

### Data Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/ingest` | POST | Receive TDS readings (requires API key) |
| `/api/latest` | GET | Get latest readings |
| `/api/latest_avg` | GET | Get latest average reading |
| `/api/history_avg` | GET | Get historical averages |

### Analysis Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/analysis_status` | GET | Get current analysis status |
| `/api/start_analysis` | POST | Manually start new analysis |
| `/api/reset_analysis` | POST | Reset current analysis |
| `/api/analysis_history` | GET | Get all past analyses |
| `/api/analysis_detail/<id>` | GET | Get specific analysis by ID |

## 🎨 UI Features

### Dashboard
- **Live Status Badge** - Shows device connection status
- **Progress Bar** - Visual indicator during data collection (0-10)
- **Analysis Card** - Displays current/historical analysis results
- **Current Readings** - Real-time TDS, voltage, and raw values
- **Recent Readings Table** - Last 10 readings in table format

### Sidebar
- **Analysis History** - Clickable list of past analyses
- **Timestamps** - Relative time display (e.g., "2h ago")
- **Quick Access** - Click any historical test to view results
- **Health Stats** - Shows total tests and readings count

### Animations
- Pulsing status indicators
- Progress bar shimmer effect
- Smooth fade-in transitions
- Loading spinners

## 🗄️ Database Schema

### Tables

**raw_readings**
- Stores every individual reading from sensors
- Fields: `id`, `device_id`, `tds_ppm`, `voltage`, `raw`, `ts_iso`, `ts_epoch`

**averaged_readings**
- Rolling 10-reading averages
- Fields: `id`, `device_id`, `avg_tds_ppm`, `window_count`, `ts_iso`, `ts_epoch`

**analysis_history**
- Complete analyses with AI explanations
- Fields: `id`, `device_id`, `avg_tds_ppm`, `ai_explanation`, `reading_count`, `ts_iso`, `ts_epoch`

## 🔧 Configuration

### Environment Variables

```bash
# Required
GEMINI_API_KEY=your-gemini-api-key

# Optional
API_KEY=flaskapp-tdsvalue          # Change for security
DB_PATH=/path/to/database.db       # Custom database location
```

### Customization

**Change refresh rate** (in `templates/index.html`):
```javascript
setInterval(checkAnalysisStatus, 2000); // Change 2000 to desired ms
setInterval(loadLatest, 2000);
```

**Change number of readings** (in `app.py`):
```python
compute_last_n_avg(db, device_id, 10)  # Change 10 to desired count
```

**Customize AI prompt** (in `app.py`, `get_tds_explanation()` function)

## 🎯 TDS Water Quality Guidelines

| TDS Level (ppm) | Quality | Description |
|----------------|---------|-------------|
| 0-50 | Excellent | Ideal for drinking |
| 50-150 | Good | Acceptable for drinking |
| 150-300 | Fair | Still drinkable |
| 300-600 | Poor | Not recommended |
| 600+ | Unacceptable | Not safe for drinking |

## 🐛 Troubleshooting

### Device Not Connecting
- Check API key in sensor code matches `API_KEY` env variable
- Verify sensor is sending to correct endpoint URL
- Check network connectivity
- Look at Flask console for error messages

### AI Analysis Not Working
- Verify `GEMINI_API_KEY` is set correctly
- Check Gemini API quota/limits
- Look for error messages in Flask console
- Ensure internet connection is available

### Database Issues
- Check write permissions in directory
- Verify SQLite is installed
- Delete `tds.db` to reset database

## 📝 Development

### Project Structure
```
tds-app/
├── app.py                  # Main Flask application
├── requirements.txt        # Python dependencies
├── tds.db                 # SQLite database (auto-created)
├── templates/
│   ├── base.html          # Base template with sidebar
│   └── index.html         # Main dashboard
└── static/
    └── css/
        └── style.css      # All styling
```

### Running in Production

**Using Gunicorn:**
```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

**Using Docker:**
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
ENV GEMINI_API_KEY=your-key
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
```

## 🤝 Contributing

Feel free to open issues or submit pull requests!

## 📄 License

MIT License - feel free to use this project for any purpose.

## 🙏 Credits

- Built with Flask and Google Gemini AI
- UI inspired by modern dashboard designs
- TDS monitoring for water quality analysis

---

**Need help?** Check the troubleshooting section or open an issue!
