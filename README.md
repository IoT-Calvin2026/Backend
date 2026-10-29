# Garden Guard Backend

Flask API for the Garden Guard Firestore database.

## Local setup

From the `Backend` directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Set `FIREBASE_SERVICE_ACCOUNT` in `.env` to the absolute path of the private
Firebase service-account JSON file. Do not commit `.env` or the JSON file.

Start the development server:

```bash
python app.py
```

The API runs at `http://localhost:5000` by default. `FLASK_DEBUG=true` and
`FLASK_HOST=0.0.0.0` are intended for local development only.

## API endpoints

All collection endpoints accept an optional `limit` query parameter from 1 to
100. The default is 25.

| Method | Route | Firestore source |
| --- | --- | --- |
| GET | `/` or `/api/health` | Backend and Firestore health |
| GET | `/api/events` | `events` |
| GET | `/api/events/<document_id>` | One `events` document |
| GET | `/api/motion` | `motion` |
| GET | `/api/motion/<document_id>` | One `motion` document |
| GET | `/api/soil-moisture` | `soil_moisture` |
| GET | `/api/soil-moisture/<document_id>` | One `soil_moisture` document |
| GET | `/api/readings/latest` | Latest timestamped document from each data collection |

Firestore timestamps and document references are converted to JSON-safe values.
Missing documents return `404`; invalid limits return `400`; Firestore
availability failures return `503`. The latest-readings route returns `null`
for a collection until its documents contain a `createdAt` or `timestamp`
field; it does not guess based on document ID or query order.

## Data flow

The intended flow is:

```text
Raspberry Pi sensors/camera
    -> MQTT broker
    -> backend MQTT subscriber (planned)
    -> Firestore
    -> Flask read endpoints
    -> frontend
```

The Raspberry Pi and MQTT subscriber are intentionally not implemented in this
repository yet. Until that subscriber exists, the API reads the existing
`events`, `motion`, and `soil_moisture` collections.

## CORS

Set `FRONTEND_ORIGINS` in `.env` to the exact Live Server origins being used,
separated by commas. For example:

```text
FRONTEND_ORIGINS=http://localhost:5500,http://127.0.0.1:5500
```

Do not use a wildcard origin once the application handles private data.
