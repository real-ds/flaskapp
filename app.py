# app.py
import os
import sqlite3
import json
from datetime import datetime, timezone, timedelta
from flask import Flask, request, jsonify, render_template, g
from flask_cors import CORS
import google.generativeai as genai

app = Flask(__name__)
CORS(app)

API_KEY = os.environ.get("API_KEY", "flaskapp-tdsvalue")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyBOeUTPHwHZgZ4NlnPiXmvPXfsuYKHPshg")
DB_PATH = os.environ.get("DB_PATH", os.path.join(os.path.dirname(__file__), "tds.db"))

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash')

# In-memory latest cache
latest = {}  # { device_id: {device_id, tds, voltage, raw, ts} }

# In-memory analysis state per device
analysis_state = {}  # { device_id: { status, reading_count, readings_sum, avg_tds, explanation, started_at, session_id } }

# --- SQLite helpers (Flask pattern) ---
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA journal_mode=WAL")
    return g.db

@app.teardown_appcontext
def close_db(exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db():
    db = get_db()
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS raw_readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT NOT NULL,
            tds_ppm REAL NOT NULL,
            voltage REAL,
            raw REAL,
            ts_iso TEXT NOT NULL,
            ts_epoch INTEGER NOT NULL,
            session_id TEXT
        );

        CREATE TABLE IF NOT EXISTS averaged_readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT NOT NULL,
            avg_tds_ppm REAL NOT NULL,
            window_count INTEGER NOT NULL,
            ts_iso TEXT NOT NULL,
            ts_epoch INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS analysis_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT NOT NULL,
            avg_tds_ppm REAL NOT NULL,
            ai_explanation TEXT NOT NULL,
            reading_count INTEGER NOT NULL,
            ts_iso TEXT NOT NULL,
            ts_epoch INTEGER NOT NULL,
            session_id TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_raw_device_time ON raw_readings(device_id, ts_epoch DESC);
        CREATE INDEX IF NOT EXISTS idx_avg_device_time ON averaged_readings(device_id, ts_epoch DESC);
        CREATE INDEX IF NOT EXISTS idx_analysis_device_time ON analysis_history(device_id, ts_epoch DESC);
        CREATE INDEX IF NOT EXISTS idx_raw_session ON raw_readings(device_id, session_id);
        """
    )
    db.commit()

with app.app_context():
    init_db()

# --- Gemini AI Analysis ---
def get_tds_explanation(tds_value: float) -> str:
    """Get layman explanation of TDS value from Gemini"""
    try:
        prompt = f"""You are a water quality expert. Explain what a TDS (Total Dissolved Solids) reading of {tds_value:.1f} ppm means for water in simple, easy-to-understand terms. Suppose from The Slum person perspective, where can they should not/should use this water. Give some Examples. 

Please cover:
1. What this TDS level means (Excellent/Good/Fair/Poor)
2. Is it safe to drink?
3. What might be dissolved in the water at this level?
4. Any recommendations for the user

Keep it conversational, friendly, and under 150 words. Use simple language that anyone can understand."""

        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Unable to generate AI explanation at this time. TDS Value: {tds_value:.1f} ppm. (Error: {str(e)})"

# --- Routes ---
@app.post("/ingest")
def ingest():
    # header API key
    if request.headers.get("X-API-Key") != API_KEY:
        return jsonify({"error": "unauthorized"}), 401

    # Parse JSON safely
    data = request.get_json(silent=True) or {}
    device_id = data.get("device_id", "device-1")
    tds_ppm = float(data.get("tds", 0.0))
    voltage = data.get("voltage")
    raw = data.get("raw")

    now = datetime.now(timezone.utc)
    ts_iso = now.isoformat()
    ts_epoch = int(now.timestamp())

    # Initialize analysis state if not exists
    if device_id not in analysis_state:
        session_id = f"{device_id}_{ts_epoch}"
        analysis_state[device_id] = {
            "status": "collecting",
            "reading_count": 0,
            "readings_sum": 0.0,
            "avg_tds": None,
            "explanation": None,
            "started_at": ts_iso,
            "session_id": session_id
        }
    
    state = analysis_state[device_id]
    
    # Only accept readings if we haven't completed 10 yet
    if state["reading_count"] < 10:
        # Store raw reading with session_id
        db = get_db()
        db.execute(
            """
            INSERT INTO raw_readings (device_id, tds_ppm, voltage, raw, ts_iso, ts_epoch, session_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (device_id, tds_ppm, voltage, raw, ts_iso, ts_epoch, state["session_id"]),
        )
        db.commit()

        # Update state
        state["reading_count"] += 1
        state["readings_sum"] += tds_ppm
        
        print(f"📊 {device_id}: Reading {state['reading_count']}/10 - TDS: {tds_ppm:.1f} ppm")

        # Check if we've reached 10 readings
        if state["reading_count"] == 10:
            # Calculate average of EXACTLY these 10 readings
            avg_tds = state["readings_sum"] / 10.0
            state["avg_tds"] = avg_tds
            state["status"] = "analyzing"
            
            print(f"✅ {device_id}: Collected 10 readings. Average: {avg_tds:.1f} ppm")
            print(f"🤖 {device_id}: Starting AI analysis...")
            
            # Get AI explanation
            explanation = get_tds_explanation(avg_tds)
            state["explanation"] = explanation
            state["status"] = "complete"
            
            print(f"✨ {device_id}: Analysis complete!")
            
            # Save to history
            db.execute(
                """
                INSERT INTO analysis_history (device_id, avg_tds_ppm, ai_explanation, reading_count, ts_iso, ts_epoch, session_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (device_id, avg_tds, explanation, 10, ts_iso, ts_epoch, state["session_id"])
            )
            db.commit()
            
            # Store averaged reading (for compatibility)
            db.execute(
                """
                INSERT INTO averaged_readings (device_id, avg_tds_ppm, window_count, ts_iso, ts_epoch)
                VALUES (?, ?, ?, ?, ?)
                """,
                (device_id, avg_tds, 10, ts_iso, ts_epoch),
            )
            db.commit()

    else:
        print(f"⚠️ {device_id}: Ignoring reading - session complete (10/10 collected)")

    # Keep legacy in-memory latest for current UI
    latest[device_id] = {
        "device_id": device_id,
        "tds": tds_ppm,
        "voltage": voltage,
        "raw": raw,
        "ts": ts_iso,
    }

    return jsonify({
        "ok": True, 
        "reading_count": state["reading_count"],
        "avg_tds_ppm": state.get("avg_tds"),
        "status": state["status"]
    })

@app.get("/api/latest")
def api_latest():
    # legacy list for current UI
    return jsonify(list(latest.values()))

@app.get("/api/latest_avg")
def api_latest_avg():
    device_id = request.args.get("device_id", "device-1")
    db = get_db()
    row = db.execute(
        """
        SELECT device_id, avg_tds_ppm, window_count, ts_iso, ts_epoch
        FROM averaged_readings
        WHERE device_id = ?
        ORDER BY ts_epoch DESC
        LIMIT 1
        """,
        (device_id,),
    ).fetchone()
    if not row:
        return jsonify({"device_id": device_id, "avg_tds_ppm": None, "window_count": 0, "ts_iso": None}), 200
    return jsonify(dict(row)), 200

@app.get("/api/history_avg")
def api_history_avg():
    device_id = request.args.get("device_id", "device-1")
    hours = int(request.args.get("hours", 24))
    cutoff_epoch = int((datetime.now(timezone.utc) - timedelta(hours=hours)).timestamp())
    db = get_db()
    rows = db.execute(
        """
        SELECT ts_iso, ts_epoch, avg_tds_ppm
        FROM averaged_readings
        WHERE device_id = ? AND ts_epoch >= ?
        ORDER BY ts_epoch ASC
        """,
        (device_id, cutoff_epoch),
    ).fetchall()
    return jsonify([dict(r) for r in rows]), 200

# --- NEW: Analysis endpoints ---
@app.post("/api/start_analysis")
def start_analysis():
    """Manually trigger analysis for a device"""
    data = request.get_json(silent=True) or {}
    device_id = data.get("device_id", "device-1")
    
    now = datetime.now(timezone.utc)
    session_id = f"{device_id}_{int(now.timestamp())}"
    
    # Initialize analysis state
    analysis_state[device_id] = {
        "status": "collecting",
        "reading_count": 0,
        "readings_sum": 0.0,
        "avg_tds": None,
        "explanation": None,
        "started_at": now.isoformat(),
        "session_id": session_id
    }
    
    print(f"🆕 {device_id}: New analysis session started - {session_id}")
    
    return jsonify({"ok": True, "message": "Analysis started", "session_id": session_id})

@app.get("/api/analysis_status")
def get_analysis_status():
    """Get current analysis status for a device"""
    device_id = request.args.get("device_id", "device-1")
    
    if device_id not in analysis_state:
        return jsonify({
            "status": "idle",
            "reading_count": 0,
            "avg_tds": None,
            "explanation": None,
            "device_connected": device_id in latest
        })
    
    state = analysis_state[device_id]
    device_connected = device_id in latest
    
    return jsonify({
        "status": state.get("status", "idle"),
        "reading_count": state.get("reading_count", 0),
        "avg_tds": state.get("avg_tds"),
        "explanation": state.get("explanation"),
        "device_connected": device_connected,
        "started_at": state.get("started_at")
    })

@app.post("/api/reset_analysis")
def reset_analysis():
    """Reset analysis state for a device"""
    data = request.get_json(silent=True) or {}
    device_id = data.get("device_id", "device-1")
    
    now = datetime.now(timezone.utc)
    session_id = f"{device_id}_{int(now.timestamp())}"
    
    # Reset to fresh state
    analysis_state[device_id] = {
        "status": "idle",
        "reading_count": 0,
        "readings_sum": 0.0,
        "avg_tds": None,
        "explanation": None,
        "started_at": None,
        "session_id": session_id
    }
    
    print(f"🔄 {device_id}: Analysis reset - Ready for new session")
    
    return jsonify({"ok": True, "message": "Analysis reset", "session_id": session_id})

@app.get("/api/analysis_history")
def get_analysis_history():
    """Get all analysis history"""
    device_id = request.args.get("device_id")
    limit = int(request.args.get("limit", 50))
    
    db = get_db()
    
    if device_id:
        rows = db.execute(
            """
            SELECT id, device_id, avg_tds_ppm, ai_explanation, reading_count, ts_iso, ts_epoch
            FROM analysis_history
            WHERE device_id = ?
            ORDER BY ts_epoch DESC
            LIMIT ?
            """,
            (device_id, limit),
        ).fetchall()
    else:
        rows = db.execute(
            """
            SELECT id, device_id, avg_tds_ppm, ai_explanation, reading_count, ts_iso, ts_epoch
            FROM analysis_history
            ORDER BY ts_epoch DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    
    return jsonify([dict(r) for r in rows])

@app.get("/api/analysis_detail/<int:analysis_id>")
def get_analysis_detail(analysis_id):
    """Get specific analysis details"""
    db = get_db()
    row = db.execute(
        """
        SELECT id, device_id, avg_tds_ppm, ai_explanation, reading_count, ts_iso, ts_epoch
        FROM analysis_history
        WHERE id = ?
        """,
        (analysis_id,),
    ).fetchone()
    
    if not row:
        return jsonify({"error": "Analysis not found"}), 404
    
    return jsonify(dict(row))

@app.get("/")
def index():
    return render_template("index.html")

@app.get("/healthz")
def healthz():
    # returns count of raw rows to confirm DB writes
    db = get_db()
    c = db.execute("SELECT COUNT(*) AS n FROM raw_readings").fetchone()
    h = db.execute("SELECT COUNT(*) AS n FROM analysis_history").fetchone()
    return jsonify({
        "ok": True, 
        "devices": len(latest), 
        "raw_rows": int(c["n"]),
        "analysis_count": int(h["n"])
    }), 200

# --- Mock Data for Neighbourhoods ---
# This is a FAKE dataset. Replace with real data if you find a source.
MOCK_NEIGHBOURHOOD_DATA = [
    {
        "id": 1,
        "name": "Vyasarpadi",
        "location": "North Chennai",
        "tds": 850.5,
        "last_updated": "2025-11-05T02:00:00Z"
    },
    {
        "id": 2,
        "name": "Nochikuppam",
        "location": "Mylapore",
        "tds": 1120.0,
        "last_updated": "2025-11-05T01:30:00Z"
    },
    {
        "id": 3,
        "name": "Saidapet (Adyar River Bank)",
        "location": "South-West Chennai",
        "tds": 910.2,
        "last_updated": "2025-11-04T23:00:00Z"
    },
    {
        "id": 4,
        "name": "Pudupet",
        "location": "Near Egmore",
        "tds": 450.8,
        "last_updated": "2025-11-05T01:15:00Z"
    },
    {
        "id": 5,
        "name": "Kannagi Nagar",
        "location": "OMR",
        "tds": 275.0,
        "last_updated": "2025-11-04T22:00:00Z"
    },
    {
        "id": 6,
        "name": "Sathya Nagar",
        "location": "Perambur",
        "tds": 610.0,
        "last_updated": "2025-11-05T00:00:00Z"
    }
]

# --- New Route for Mock API ---
@app.get("/api/neighbourhood_data")
def api_neighbourhood_data():
    """Serves the mock neighbourhood TDS data."""
    return jsonify(MOCK_NEIGHBOURHOOD_DATA)

# --- New Route for the Page ---
@app.get("/neighbourhood")
def neighbourhood():
    """Renders the new Neighbourhood Data page."""
    return render_template("neighbourhood.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)