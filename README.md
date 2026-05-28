# Appointment Service

Independent FastAPI service for booking, appointment history, cancellation, and booking notifications.

## Run

```bash
cp .env.example .env
pip install -r requirements.txt
PYTHONPATH=. uvicorn src.appointment_service.main:app --reload --port 8002
```

## Test

```bash
pytest
```

## Docker

```bash
docker compose up --build
```
