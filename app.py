import os
from datetime import date, datetime
from typing import Any

import firebase_admin
from dotenv import load_dotenv
from firebase_admin import credentials, firestore
from flask import Flask, jsonify, request
from flask_cors import CORS
from google.api_core.exceptions import GoogleAPIError

load_dotenv()

app = Flask(__name__)

allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "FRONTEND_ORIGINS",
        "http://localhost:5500,http://127.0.0.1:5500",
    ).split(",")
    if origin.strip()
]
CORS(app, origins=allowed_origins)

service_account_path = os.getenv("FIREBASE_SERVICE_ACCOUNT")
if not service_account_path:
    raise RuntimeError("FIREBASE_SERVICE_ACCOUNT must be set in Backend/.env")

if not firebase_admin._apps:
    firebase_admin.initialize_app(credentials.Certificate(service_account_path))

db = firestore.client()


def serialize_value(value: Any) -> Any:
    """Convert Firestore-specific values into JSON-compatible values."""
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, firestore.DocumentReference):
        return value.path
    if isinstance(value, dict):
        return {key: serialize_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [serialize_value(item) for item in value]
    return value


def serialize_document(document: Any) -> dict[str, Any]:
    return {
        "id": document.id,
        **serialize_value(document.to_dict() or {}),
    }


def requested_limit() -> int:
    raw_limit = request.args.get("limit", "25")
    try:
        limit = int(raw_limit)
    except ValueError as error:
        raise ValueError("limit must be an integer between 1 and 100") from error
    if not 1 <= limit <= 100:
        raise ValueError("limit must be an integer between 1 and 100")
    return limit


def collection_documents(collection_name: str) -> list[dict[str, Any]]:
    documents = (
        db.collection(collection_name)
        .limit(requested_limit())
        .stream()
    )
    return [serialize_document(document) for document in documents]


def collection_document(collection_name: str, document_id: str) -> dict[str, Any]:
    document = db.collection(collection_name).document(document_id).get()
    if not document.exists:
        return {}
    return serialize_document(document)


def latest_document(collection_name: str) -> dict[str, Any] | None:
    for timestamp_field in ("createdAt", "timestamp"):
        documents = (
            db.collection(collection_name)
            .order_by(timestamp_field, direction=firestore.Query.DESCENDING)
            .limit(1)
            .stream()
        )
        document = next(iter(documents), None)
        if document is not None:
            return serialize_document(document)
    return None


@app.errorhandler(ValueError)
def handle_bad_request(error: ValueError):
    return jsonify({"error": str(error)}), 400


@app.errorhandler(GoogleAPIError)
def handle_firestore_error(error: GoogleAPIError):
    app.logger.exception("Firestore request failed")
    return jsonify({"error": "Firestore is unavailable"}), 503


@app.get("/")
@app.get("/api/health")
def health_check():
    try:
        next(iter(db.collection("events").limit(1).stream()), None)
    except GoogleAPIError:
        app.logger.exception("Firestore health check failed")
        return jsonify({"status": "degraded", "firestore": "unavailable"}), 503
    return jsonify({"status": "ok", "firestore": "connected"})


@app.get("/api/events")
def get_events():
    return jsonify(collection_documents("events"))


@app.get("/api/events/<document_id>")
def get_event(document_id: str):
    event = collection_document("events", document_id)
    if not event:
        return jsonify({"error": "Event not found"}), 404
    return jsonify(event)


@app.get("/api/motion")
def get_motion_events():
    return jsonify(collection_documents("motion"))


@app.get("/api/motion/<document_id>")
def get_motion_event(document_id: str):
    event = collection_document("motion", document_id)
    if not event:
        return jsonify({"error": "Motion event not found"}), 404
    return jsonify(event)


@app.get("/api/soil-moisture")
def get_soil_moisture():
    return jsonify(collection_documents("soil_moisture"))


@app.get("/api/soil-moisture/<document_id>")
def get_soil_moisture_reading(document_id: str):
    reading = collection_document("soil_moisture", document_id)
    if not reading:
        return jsonify({"error": "Soil-moisture reading not found"}), 404
    return jsonify(reading)


@app.get("/api/readings/latest")
def get_latest_readings():
    readings = {
        "soilMoisture": latest_document("soil_moisture"),
        "motion": latest_document("motion"),
        "events": latest_document("events"),
    }
    return jsonify(readings)


if __name__ == "__main__":
    host = os.getenv("FLASK_HOST", "0.0.0.0")
    port = int(os.getenv("FLASK_PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "true").lower() == "true"
    app.run(host=host, port=port, debug=debug)