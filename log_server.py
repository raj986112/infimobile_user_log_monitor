from flask import Flask, request, jsonify
from datetime import datetime
import sqlite3
import os

from sklearn.ensemble import IsolationForest
import pandas as pd

app = Flask(__name__)
DB_NAME = '/home/aryagami/infimobile_user_log_monitor/logs.db'

# ----------------------------
# Database Initialization
# ----------------------------
def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT,
                message TEXT,
                device TEXT,
                android_version TEXT,
                timestamp TEXT,
                received_at TEXT
            )
        ''')
        conn.commit()

# ----------------------------
# Save Log to Database
# ----------------------------
def save_log_to_db(data):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO logs (type, message, device, android_version, timestamp, received_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            data.get("type"),
            data.get("message"),
            data.get("device"),
            data.get("android_version"),
            str(data.get("timestamp")),
            data.get("received_at")
        ))
        conn.commit()

# ----------------------------
# Fetch Logs from Database
# ----------------------------
def fetch_logs(log_type=None):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        if log_type:
            cursor.execute('SELECT * FROM logs WHERE type = ?', (log_type,))
        else:
            cursor.execute('SELECT * FROM logs')
        rows = cursor.fetchall()
    logs = [{
        "id": row[0],
        "type": row[1],
        "message": row[2],
        "device": row[3],
        "android_version": row[4],
        "timestamp": row[5],
        "received_at": row[6]
    } for row in rows]
    return logs

# ----------------------------
# API: Receive Logs
# ----------------------------
@app.route("/log", methods=["POST"])
def receive_log():
    try:
        data = request.get_json()
        data["received_at"] = datetime.now().isoformat()
        save_log_to_db(data)
        print("📥 Log saved to database:", data)
        return jsonify({"status": "success"}), 200
    except Exception as e:
        print("❌ Error:", e)
        return jsonify({"status": "error", "message": str(e)}), 500

# ----------------------------
# API: Get Logs with Optional Filter
# ----------------------------
@app.route("/logs", methods=["GET"])
def get_logs():
    log_type = request.args.get("type")  # e.g., "CRASH", "API_ERROR"
    logs = fetch_logs(log_type)
    return jsonify(logs), 200

# ----------------------------
# API: Detect Anomalies
# ----------------------------
@app.route("/anomaly", methods=["GET"])
def detect_anomalies():
    logs = fetch_logs()
    if not logs:
        return jsonify({"error": "No logs found"}), 404

    # Create DataFrame
    df = pd.DataFrame(logs)

    # Filter only relevant error types
    df = df[df["type"].isin(["API_ERROR", "CRASH"])]

    if df.empty:
        return jsonify({"message": "No API errors or crashes found."}), 200

    # Convert and group by hour
    df["hour"] = pd.to_datetime(df["received_at"]).dt.floor("H")
    grouped = df.groupby("hour").size().reset_index(name="log_count")

    # AI Model - Isolation Forest
    model = IsolationForest(contamination=0.2, random_state=42)
    grouped["anomaly"] = model.fit_predict(grouped[["log_count"]])

    # Extract anomalies
    anomalies = grouped[grouped["anomaly"] == -1]
    results = anomalies.to_dict(orient="records")
    return jsonify({"anomalies": results}), 200

# ----------------------------
# Main
# ----------------------------
if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000)

