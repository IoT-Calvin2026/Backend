"""Seed Firestore with mock data. Run from Backend/:  python seed_data.py
Add --clear to wipe the three collections first."""
import os
import random
import sys
from datetime import datetime, timedelta, timezone

import firebase_admin
from dotenv import load_dotenv
from firebase_admin import credentials, firestore

load_dotenv()
firebase_admin.initialize_app(credentials.Certificate(os.environ["FIREBASE_SERVICE_ACCOUNT"]))
db = firestore.client()

ZONES = ["Tomato bed", "Herb garden", "Greenhouse", "Front lawn"]
random.seed(7)
now = datetime.now(timezone.utc)


def clear(name):
    for doc in db.collection(name).stream():
        doc.reference.delete()


def add(name, data):
    # Both fields so /api/readings/latest works whichever one it tries.
    data["createdAt"] = data["timestamp"]
    db.collection(name).add(data)


if "--clear" in sys.argv:
    for name in ("soil_moisture", "motion", "events"):
        clear(name)

# Soil moisture: every 30 min for 48 h, per zone, with slow drying + watering bumps.
for zone in ZONES:
    level = random.uniform(45, 65)
    for i in range(96, 0, -1):
        level = max(12, level - random.uniform(0.2, 1.1))
        if level < 28 and random.random() < 0.4:  # watering event
            level += random.uniform(25, 35)
        add("soil_moisture", {
            "zone": zone,
            "moisturePercent": round(min(level, 95), 1),
            "temperatureC": round(random.uniform(14, 27), 1),
            "sensorId": f"sm-{ZONES.index(zone) + 1:02d}",
            "timestamp": now - timedelta(minutes=30 * i),
        })

# Motion: ~60 detections over 48 h.
for _ in range(60):
    zone = random.choice(ZONES)
    add("motion", {
        "zone": zone,
        "detected": True,
        "durationSeconds": random.randint(2, 45),
        "sensorId": f"pir-{ZONES.index(zone) + 1:02d}",
        "timestamp": now - timedelta(minutes=random.randint(1, 48 * 60)),
    })

# Events: watering, alerts, device status.
templates = [
    ("watering_started", "info", "Irrigation started in {z}"),
    ("watering_stopped", "info", "Irrigation finished in {z}"),
    ("low_moisture", "warning", "Soil moisture below 25% in {z}"),
    ("motion_alert", "warning", "Unexpected movement near {z}"),
    ("sensor_offline", "critical", "Sensor in {z} stopped reporting"),
    ("sensor_online", "info", "Sensor in {z} reconnected"),
]
for _ in range(30):
    kind, severity, msg = random.choice(templates)
    zone = random.choice(ZONES)
    add("events", {
        "type": kind,
        "severity": severity,
        "zone": zone,
        "message": msg.format(z=zone),
        "timestamp": now - timedelta(minutes=random.randint(1, 48 * 60)),
    })

print("Seeded soil_moisture (384), motion (60), events (30).")