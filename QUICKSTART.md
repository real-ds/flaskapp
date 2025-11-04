# 🚀 Quick Start Guide

Get your WaterWatch TDS Monitor running in 5 minutes!

## Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

## Step 2: Set Up Gemini API Key

1. Get your free API key from: https://makersuite.google.com/app/apikey
2. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
3. Edit `.env` and replace `your-gemini-api-key-here` with your actual key:
   ```bash
   GEMINI_API_KEY=AIzaSyAbc123...your-key-here
   ```

## Step 3: Run the Application

```bash
python app.py
```

You should see:
```
 * Running on http://0.0.0.0:5000
```

## Step 4: Open the Dashboard

Open your browser and go to:
```
http://localhost:5000
```

## Step 5: Test with Simulated Data

In a new terminal, run the test sensor simulator:

```bash
python test_sensor.py excellent 15 1.0
```

This will:
- ✅ Send 15 readings of excellent water quality
- ⏱️ One reading per second
- 📊 Trigger automatic analysis after 10 readings
- 🤖 Generate AI explanation via Gemini

## What You'll See

1. **Device Connects** - Green badge appears saying "Device Connected"
2. **Progress Bar** - Shows "Collecting readings... 1/10, 2/10..." up to 10/10
3. **AI Analysis** - Spinner shows "AI is analyzing your water quality..."
4. **Results Display** - Shows:
   - Average TDS value (e.g., 125.4 ppm)
   - Quality badge (Excellent/Good/Fair/Poor)
   - AI explanation in plain English
5. **History Saved** - Analysis appears in left sidebar history

## Try Different Water Quality Scenarios

### Excellent Water (50-150 ppm)
```bash
python test_sensor.py excellent 15 1.0
```

### Good Water (150-300 ppm)
```bash
python test_sensor.py good 15 1.0
```

### Fair Water (300-500 ppm)
```bash
python test_sensor.py fair 15 1.0
```

### Poor Water (500-800 ppm)
```bash
python test_sensor.py poor 15 1.0
```

## Continuous Monitoring Mode

For continuous testing (press Ctrl+C to stop):
```bash
python test_sensor.py continuous excellent 1.0
```

## Connect Real TDS Sensor

Your sensor should POST to: `http://your-server:5000/ingest`

**Headers:**
```
X-API-Key: flaskapp-tdsvalue
Content-Type: application/json
```

**Body:**
```json
{
  "device_id": "device-1",
  "tds": 245.5,
  "voltage": 3.28,
  "raw": 1024
}
```

See `README.md` for complete sensor integration examples (Arduino, ESP32, Python, etc.)

## Troubleshooting

### "Connection Error"
- Make sure Flask app is running: `python app.py`
- Check the URL is correct: `http://localhost:5000`

### "401 Unauthorized"
- Check API_KEY in `.env` matches what sensor is sending
- Default is: `flaskapp-tdsvalue`

### "Gemini API Error"
- Verify GEMINI_API_KEY is set in `.env`
- Check your API quota at https://makersuite.google.com
- Make sure you have internet connection

### No Analysis Happening
- Wait for at least 10 readings to be collected
- Check Flask console for errors
- Try running `python test_sensor.py excellent 15 1.0`

## Next Steps

✅ View past analyses by clicking items in the history sidebar  
✅ Click "New Analysis" button to start fresh  
✅ Connect your real TDS sensor (see README.md)  
✅ Deploy to production (see README.md for Docker/Gunicorn setup)  

---

**Need More Help?** Check the full `README.md` file for detailed documentation!
