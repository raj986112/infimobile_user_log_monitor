import sqlite3
import pandas as pd
import streamlit as st
from sklearn.ensemble import IsolationForest
from datetime import datetime, timedelta
from streamlit_toggle import st_toggle_switch

import random
import os
import shutil

# -----------------------------------
# Setup DB path (Railway-compatible)
# -----------------------------------
DB_NAME = '/tmp/logs.db'

# Copy prebuilt DB to writable location in Railway
if not os.path.exists(DB_NAME):
    if os.path.exists('logs.db'):
        shutil.copy('logs.db', DB_NAME)
    else:
        raise FileNotFoundError("logs.db not found in project root. Please add it to your repository.")

# -----------------------------------
# Theme toggle
# -----------------------------------
theme_mode = st_toggle_switch(
    label="🎨 Theme",
    key="theme",
    default_value=True,
    label_after=False,
    inactive_color="#D3D3D3",
    active_color="#00FFFF",
    track_color="#8A2BE2"
)

# -----------------------------------
# Load logs from DB
# -----------------------------------
@st.cache_data
def load_logs():
    try:
        with sqlite3.connect(DB_NAME) as conn:
            df = pd.read_sql_query("SELECT * FROM logs", conn)

        df['received_at'] = pd.to_datetime(df['received_at'], errors='coerce')
        df = df.dropna(subset=['received_at'])
        df['user'] = df['user'].fillna('unknown').replace('', 'unknown')
        return df
    except Exception as e:
        st.error(f"❌ Error loading logs: {e}")
        return pd.DataFrame()

# -----------------------------------
# Detect anomalies
# -----------------------------------
def detect_anomalies(df):
    df_grouped = df.copy()
    df_grouped["hour"] = df_grouped["received_at"].dt.floor("h")
    grouped = df_grouped.groupby("hour").size().reset_index(name="log_count")
    if len(grouped) < 5:
        return grouped, pd.DataFrame()
    model = IsolationForest(contamination=0.2)
    grouped["anomaly"] = model.fit_predict(grouped[["log_count"]])
    anomalies = grouped[grouped["anomaly"] == -1]
    return grouped, anomalies

# -----------------------------------
# Insert dummy logs
# -----------------------------------
def insert_dummy_logs():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        devices = ["Pixel 5", "Samsung S21", "Redmi Note 10", "OnePlus 9", "Realme 8"]
        versions = ["11", "12", "13", "14"]
        types = ["API_ERROR", "CRASH", "INFO"]
        messages = [
            "NullPointerException at MainActivity",
            "Timeout while calling /login API",
            "App crashed unexpectedly",
            "Handled API failure gracefully",
            "User clicked retry too fast"
        ]
        users = ["raj@infimobile.com", "qa@test.com", "dev1@demo.com", "beta@android.com", "test@sample.com"]

        for _ in range(10):
            ts = datetime.now() - timedelta(minutes=random.randint(0, 120))
            cursor.execute('''
                INSERT INTO logs (type, message, device, android_version, timestamp, received_at, user)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                random.choice(types),
                random.choice(messages),
                random.choice(devices),
                random.choice(versions),
                ts.isoformat(),
                ts.isoformat(),
                random.choice(users)
            ))
        conn.commit()

# -----------------------------------
# Streamlit UI Setup
# -----------------------------------
st.set_page_config(page_title="📲 Android App Log Monitor", layout="wide")

st.markdown("""
    <style>
    .stApp {
        background-color: #000000;
        color: #00FF00;
        font-family: 'Courier New', monospace;
    }

    .block-container {
        background-color: #0a0a0a;
        padding: 2rem;
        border-radius: 12px;
        box-shadow: 0 0 20px #00FF00;
    }

    .stDataFrame, .stMarkdown, .stMetric, .stTextInput, .stSelectbox, .stDateInput, .stButton, .stDownloadButton {
        color: #00FF00;
    }

    .stDataFrame {
        background-color: #101010;
        border: 1px solid #00FF00;
    }

    .stButton > button {
        background-color: #000000;
        color: #00FF00;
        border: 2px solid #00FF00;
        font-weight: bold;
        border-radius: 10px;
        box-shadow: 0 0 10px #00FF00;
        transition: all 0.3s ease-in-out;
    }

    .stButton > button:hover {
        background-color: #00FF00;
        color: black;
        transform: scale(1.05);
    }

    .stMetric label, .stSelectbox label, .stTextInput label {
        color: #00FF00;
    }

    .css-1rs6os.edgvbvh3 {
        background-color: #0a0a0a;
    }

    h1, h2, h3, h4 {
        color: #00FF00;
        text-shadow: 0 0 10px #00FF00;
    }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------
# Title & Buttons
# -----------------------------------
st.markdown("""<h1 style='text-align: center;'>📲 Android App Logs Dashboard</h1>""", unsafe_allow_html=True)

colA, colB = st.columns(2)
with colA:
    if st.button("➕ Insert Dummy Logs"):
        insert_dummy_logs()
        st.success("✅ 10 dummy logs inserted!")
        st.cache_data.clear()
        st.rerun()

with colB:
    if st.button("🔄 Refresh Logs"):
        st.cache_data.clear()
        st.rerun()

# -----------------------------------
# Load Logs
# -----------------------------------
df_logs = load_logs()
if df_logs.empty:
    st.warning("⚠️ No logs available.")
    st.stop()

# -----------------------------------
# Search
# -----------------------------------
search_keyword = st.text_input("🔍 Search Logs (message/user/device)")
if search_keyword:
    df_logs = df_logs[
        df_logs['message'].str.contains(search_keyword, case=False, na=False) |
        df_logs['user'].str.contains(search_keyword, case=False, na=False) |
        df_logs['device'].str.contains(search_keyword, case=False, na=False)
    ]

# -----------------------------------
# Filters
# -----------------------------------
col1, col2, col3 = st.columns(3)
with col1:
    types = df_logs["type"].dropna().unique().tolist()
    selected_type = st.selectbox("Filter by Type", ["ALL"] + types)
with col2:
    users = df_logs["user"].dropna().unique().tolist()
    selected_user = st.selectbox("Filter by User", ["ALL"] + users)
with col3:
    st.metric("Total Logs", len(df_logs))

if selected_type != "ALL":
    df_logs = df_logs[df_logs["type"] == selected_type]
if selected_user != "ALL":
    df_logs = df_logs[df_logs["user"] == selected_user]

# -----------------------------------
# Date Range
# -----------------------------------
min_date = df_logs["received_at"].min().date()
max_date = df_logs["received_at"].max().date()
date_range = st.date_input("📅 Date Range", [min_date, max_date])
if len(date_range) == 2:
    start_date = pd.to_datetime(date_range[0])
    end_date = pd.to_datetime(date_range[1]) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
    df_logs = df_logs[df_logs["received_at"].between(start_date, end_date)]

# -----------------------------------
# Log Table
# -----------------------------------
st.subheader("📋 Logs")
st.dataframe(
    df_logs[["id", "type", "message", "device", "android_version", "user", "received_at"]].sort_values("received_at", ascending=False),
    use_container_width=True,
    height=300
)

# -----------------------------------
# Charts
# -----------------------------------
st.subheader("📈 Log Frequency Over Time")
grouped_df, anomalies = detect_anomalies(df_logs)
st.line_chart(grouped_df.set_index("hour")["log_count"])

if not anomalies.empty:
    st.error("🚨 Anomalies Detected!")
    st.dataframe(anomalies, use_container_width=True)

# -----------------------------------
# Top Devices & Versions
# -----------------------------------
col4, col5 = st.columns(2)
with col4:
    st.subheader("📱 Top Devices")
    top_devices = df_logs.groupby("device").size().reset_index(name="count").sort_values("count", ascending=False)
    st.bar_chart(top_devices.set_index("device"))

with col5:
    st.subheader("📱 Top Android Versions")
    top_versions = df_logs.groupby("android_version").size().reset_index(name="count").sort_values("count", ascending=False)
    st.bar_chart(top_versions.set_index("android_version"))

# -----------------------------------
# CSV Export
# -----------------------------------
st.subheader("⬇️ Export Logs")
csv = df_logs.to_csv(index=False).encode("utf-8")
st.download_button("📥 Download CSV", data=csv, file_name="logs.csv", mime="text/csv")

