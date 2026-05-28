from datetime import datetime
from enum import StrEnum

from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel, Field

from src.common.database import connect, transaction
from src.common.security import current_user, require_role

app = FastAPI(title="Appointment Service", version="1.0.0")


class AppointmentStatus(StrEnum):
    booked = "Booked"
    cancelled = "Cancelled"
    completed = "Completed"


class BookAppointmentRequest(BaseModel):
    doctor_id: int = Field(gt=0)
    appointment_time: datetime
    reason: str | None = Field(default=None, max_length=500)


class CancelAppointmentRequest(BaseModel):
    appointment_id: int = Field(gt=0)


class AppointmentResponse(BaseModel):
    id: int
    patient_id: int
    doctor_id: int
    appointment_time: str
    status: AppointmentStatus
    reason: str | None
    created_at: str


def init_db() -> None:
    with transaction() as db:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS appointments (
                id INT PRIMARY KEY AUTO_INCREMENT,
                patient_id INT NOT NULL,
                doctor_id INT NOT NULL,
                appointment_time VARCHAR(40) NOT NULL,
                status ENUM('Booked', 'Cancelled', 'Completed') NOT NULL,
                reason TEXT,
                created_at VARCHAR(40) NOT NULL,
                active_booking TINYINT GENERATED ALWAYS AS (
                    CASE WHEN status = 'Booked' THEN 1 ELSE NULL END
                ) STORED,
                UNIQUE KEY idx_active_doctor_slot (doctor_id, appointment_time, active_booking)
            )
            """
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS notifications (
                id INT PRIMARY KEY AUTO_INCREMENT,
                appointment_id INT NOT NULL,
                recipient_user_id INT NOT NULL,
                message TEXT NOT NULL,
                created_at VARCHAR(40) NOT NULL
            )
            """
        )


@app.on_event("startup")
def startup() -> None:
    init_db()


def row_to_appointment(row) -> AppointmentResponse:
    return AppointmentResponse(
        id=row["id"],
        patient_id=row["patient_id"],
        doctor_id=row["doctor_id"],
        appointment_time=row["appointment_time"],
        status=row["status"],
        reason=row["reason"],
        created_at=row["created_at"],
    )


@app.post("/appointments/book", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
def book_appointment(
    payload: BookAppointmentRequest,
    user: dict = Depends(require_role("Patient", "Admin")),
) -> AppointmentResponse:
    patient_id = int(user["sub"])
    now = datetime.utcnow().isoformat()
    slot = payload.appointment_time.isoformat()
    with transaction() as db:
        existing = db.execute(
            """
            SELECT id FROM appointments
            WHERE doctor_id = ? AND appointment_time = ? AND status = 'Booked'
            """,
            (payload.doctor_id, slot),
        ).fetchone()
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Doctor already booked for this slot")

        cursor = db.execute(
            """
            INSERT INTO appointments (patient_id, doctor_id, appointment_time, status, reason, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (patient_id, payload.doctor_id, slot, AppointmentStatus.booked.value, payload.reason, now),
        )
        appointment_id = cursor.lastrowid
        db.execute(
            """
            INSERT INTO notifications (appointment_id, recipient_user_id, message, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                appointment_id,
                patient_id,
                f"Appointment {appointment_id} booked with doctor {payload.doctor_id} for {slot}.",
                now,
            ),
        )
        row = db.execute("SELECT * FROM appointments WHERE id = ?", (appointment_id,)).fetchone()
    return row_to_appointment(row)


@app.get("/appointments/history", response_model=list[AppointmentResponse])
def appointment_history(user: dict = Depends(current_user)) -> list[AppointmentResponse]:
    user_id = int(user["sub"])
    role = user["role"]
    if role == "Doctor":
        query = "SELECT * FROM appointments WHERE doctor_id = ? ORDER BY appointment_time DESC"
    elif role == "Patient":
        query = "SELECT * FROM appointments WHERE patient_id = ? ORDER BY appointment_time DESC"
    else:
        query = "SELECT * FROM appointments ORDER BY appointment_time DESC"

    with connect() as db:
        rows = db.execute(query, () if role == "Admin" else (user_id,)).fetchall()
    return [row_to_appointment(row) for row in rows]


@app.post("/appointments/cancel", response_model=AppointmentResponse)
def cancel_appointment(payload: CancelAppointmentRequest, user: dict = Depends(current_user)) -> AppointmentResponse:
    user_id = int(user["sub"])
    role = user["role"]
    with transaction() as db:
        row = db.execute("SELECT * FROM appointments WHERE id = ?", (payload.appointment_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")
        if row["status"] != AppointmentStatus.booked.value:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only booked appointments can be cancelled")
        if role == "Patient" and row["patient_id"] != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot cancel another patient's appointment")
        if role == "Doctor" and row["doctor_id"] != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot cancel another doctor's appointment")

        db.execute(
            "UPDATE appointments SET status = ? WHERE id = ?",
            (AppointmentStatus.cancelled.value, payload.appointment_id),
        )
        updated = db.execute("SELECT * FROM appointments WHERE id = ?", (payload.appointment_id,)).fetchone()
    return row_to_appointment(updated)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "appointment"}
