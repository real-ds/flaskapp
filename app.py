# app.py
import os
import sqlite3
from datetime import datetime, timezone, timedelta
from flask import Flask, request, jsonify, render_template, g
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

API_KEY = os.environ.get("API_KEY", "flaskapp-tdsvalue")
DB_PATH = os.environ.get("DB_PATH", os.path.join(os.path.dirname(__file__), "tds.db"))

# In-memory latest cache (kept for current UI; will shift to averaged endpoints next)
latest = {}  # { device_id: {device_id, tds, voltage, raw, ts} }

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
            ts_epoch INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS averaged_readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT NOT NULL,
            avg_tds_ppm REAL NOT NULL,
            window_count INTEGER NOT NULL,
            ts_iso TEXT NOT NULL,
            ts_epoch INTEGER NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_raw_device_time ON raw_readings(device_id, ts_epoch DESC);
        CREATE INDEX IF NOT EXISTS idx_avg_device_time ON averaged_readings(device_id, ts_epoch DESC);
        """
    )
    db.commit()

with app.app_context():
    init_db()

# --- Utility: compute rolling average of last 10 ---
def compute_last10_avg(db, device_id: str):
    cur = db.execute(
        """
        SELECT AVG(tds_ppm) AS avg_tds, COUNT(*) AS n
        FROM (
          SELECT tds_ppm
          FROM raw_readings
          WHERE device_id = ?
          ORDER BY id DESC
          LIMIT 10
        )
        """,
        (device_id,),
    )
    row = cur.fetchone()
    avg_tds = float(row["avg_tds"]) if row["avg_tds"] is not None else None
    count = int(row["n"] or 0)
    return avg_tds, count

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

    # Store raw reading
    db = get_db()
    db.execute(
        """
        INSERT INTO raw_readings (device_id, tds_ppm, voltage, raw, ts_iso, ts_epoch)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (device_id, tds_ppm, voltage, raw, ts_iso, ts_epoch),
    )
    db.commit()

    # Compute rolling last-10 average and persist an averaged point
    avg_tds, count = compute_last10_avg(db, device_id)
    if avg_tds is not None and count > 0:
        db.execute(
            """
            INSERT INTO averaged_readings (device_id, avg_tds_ppm, window_count, ts_iso, ts_epoch)
            VALUES (?, ?, ?, ?, ?)
            """,
            (device_id, avg_tds, count, ts_iso, ts_epoch),
        )
        db.commit()

    # Keep legacy in-memory latest for current UI
    latest[device_id] = {
        "device_id": device_id,
        "tds": tds_ppm,
        "voltage": voltage,
        "raw": raw,
        "ts": ts_iso,
    }

    return jsonify({"ok": True, "avg_tds_ppm": avg_tds, "window_count": count})

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

@app.get("/")
def index():
    return render_template("index.html")

@app.get("/healthz")
def healthz():
    # returns count of raw rows to confirm DB writes
    db = get_db()
    c = db.execute("SELECT COUNT(*) AS n FROM raw_readings").fetchone()
    return jsonify({"ok": True, "devices": len(latest), "raw_rows": int(c["n"])}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
