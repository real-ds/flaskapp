# app.py
import os
from datetime import datetime, timezone
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # restrict in production
API_KEY = os.environ.get("API_KEY", "changeme")
latest = {}  # {device_id: reading}

@app.post("/ingest")
def ingest():
    if request.headers.get("X-API-Key") != API_KEY:
        return jsonify({"error": "unauthorized"}), 401
    data = request.get_json(silent=True) or {}
    data["ts"] = datetime.now(timezone.utc).isoformat()
    dev = data.get("device_id", "unknown")
    latest[dev] = data
    return jsonify({"ok": True})

@app.get("/api/latest")
def api_latest():
    return jsonify(list(latest.values()))

@app.get("/")
def index():
    return """
<!doctype html><meta charset="utf-8">
<h2>TDS Live</h2><pre id="out">Loading...</pre>
<script>
async function refresh(){
  const r = await fetch('/api/latest');
  const j = await r.json();
  document.getElementById('out').textContent = JSON.stringify(j, null, 2);
}
setInterval(refresh, 3000); refresh();
</script>
"""
