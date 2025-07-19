import sqlite3
from datetime import datetime

log = {
    "type": "CRASH",
    "message": "Simulated crash for testing dashboard",
    "device": "Pixel 6a",
    "android_version": "14",
    "timestamp": datetime.now().isoformat(),
    "received_at": datetime.now().isoformat(),
    "user": "demo_user"
}

with sqlite3.connect("logs.db") as conn:
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO logs (type, message, device, android_version, timestamp, received_at, user)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        log["type"],
        log["message"],
        log["device"],
        log["android_version"],
        log["timestamp"],
        log["received_at"],
        log["user"]
    ))
    conn.commit()

print("✅ Dummy log inserted successfully.")
