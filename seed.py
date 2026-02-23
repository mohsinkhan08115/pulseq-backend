"""
Run once to seed the database with demo data.
Usage:  python seed.py
"""
import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal, engine, Base
from app.core.security import get_password_hash
from app.models.models import Doctor, Patient, MedicalRecord, doctor_patient

def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(Doctor).count() > 0:
            print("✅ Already seeded — skipping.")
            return

        print("🌱 Seeding database ...")

        # ── Doctors ──────────────────────────────────────────
        docs = [
            Doctor(name="Dr. Ahmed Khan",   email="ahmed@pulseq.com",
                   phone="+92 300 1234567", specialization="Cardiologist",
                   hospital="IDC Hospital", hashed_password=get_password_hash("doctor123")),
            Doctor(name="Dr. Sarah Ali",    email="sarah@pulseq.com",
                   phone="+92 321 7654321", specialization="Pediatrician",
                   hospital="City Hospital", hashed_password=get_password_hash("doctor456")),
            Doctor(name="Dr. Hassan Malik", email="hassan@pulseq.com",
                   phone="+92 333 9876543", specialization="General Physician",
                   hospital="Metro Medical", hashed_password=get_password_hash("doctor789")),
        ]
        for d in docs: db.add(d)
        db.commit()
        for d in docs: db.refresh(d)
        print(f"  ✅ {len(docs)} doctors created")

        # ── Patients ──────────────────────────────────────────
        pats = [
            Patient(name="Hamda",        email="hamda@example.com",
                    phone="+92 300 0000001", date_of_birth="2004-03-09",
                    location="Lahore",    total_visits=5, last_visit="2025-02-05",
                    medical_history_summary="Regular checkups, no chronic conditions"),
            Patient(name="Ali Khan",     email="ali@example.com",
                    phone="+92 321 0000002", date_of_birth="1990-05-15",
                    location="Karachi",   total_visits=8, last_visit="2025-02-03",
                    medical_history_summary="Hypertension patient, regular monitoring"),
            Patient(name="Fatima Ahmed", email="fatima@example.com",
                    phone="+92 333 0000003", date_of_birth="1985-08-20",
                    location="Islamabad", total_visits=12, last_visit="2025-02-01",
                    medical_history_summary="Diabetes Type 2, under medication"),
            Patient(name="Usman Raza",   email="usman@example.com",
                    phone="+92 345 0000004", date_of_birth="1995-12-10",
                    location="Lahore",    total_visits=3, last_visit="2025-01-28",
                    medical_history_summary="Asthma patient, inhaler prescribed"),
        ]
        for p in pats: db.add(p)
        db.commit()
        for p in pats: db.refresh(p)
        print(f"  ✅ {len(pats)} patients created")

        # ── Doctor-Patient links ───────────────────────────────
        links = [
            (docs[0].id, pats[0].id), (docs[0].id, pats[1].id),
            (docs[0].id, pats[2].id), (docs[1].id, pats[0].id),
            (docs[2].id, pats[3].id),
        ]
        for did, pid in links:
            db.execute(doctor_patient.insert().values(doctor_id=did, patient_id=pid))
        db.commit()
        print(f"  ✅ {len(links)} doctor-patient links created")

        # ── Medical Records ────────────────────────────────────
        recs = [
            MedicalRecord(
                patient_id=pats[0].id, doctor_id=docs[0].id,
                diagnosis="Fever and Flu", visit_date="2025-02-05",
                symptoms=["Fever", "Cough", "Headache"],
                prescription="Paracetamol 500mg TID, Rest and fluids",
                notes="Advised rest for 3 days. Drink plenty of fluids.",
                follow_up_date="2025-02-12",
                vital_signs={"temperature": "101°F", "blood_pressure": "120/80", "heart_rate": "85 bpm"},
            ),
            MedicalRecord(
                patient_id=pats[0].id, doctor_id=docs[0].id,
                diagnosis="Migraine", visit_date="2025-01-20",
                symptoms=["Severe headache", "Nausea", "Light sensitivity"],
                prescription="Sumatriptan 50mg, Rest in dark room",
                notes="Stress-related migraine. Advised stress management.",
                follow_up_date="2025-01-27",
                vital_signs={"temperature": "98.6°F", "blood_pressure": "115/75", "heart_rate": "78 bpm"},
            ),
            MedicalRecord(
                patient_id=pats[0].id, doctor_id=docs[1].id,
                diagnosis="Allergic Rhinitis", visit_date="2024-12-15",
                symptoms=["Sneezing", "Runny nose", "Itchy eyes"],
                prescription="Cetirizine 10mg OD, Nasal spray",
                notes="Seasonal allergies. Avoid dust and pollen.",
                vital_signs={"temperature": "98.4°F", "blood_pressure": "118/76", "heart_rate": "72 bpm"},
            ),
            MedicalRecord(
                patient_id=pats[1].id, doctor_id=docs[0].id,
                diagnosis="Hypertension Follow-up", visit_date="2025-02-03",
                symptoms=["Elevated BP", "Slight dizziness"],
                prescription="Amlodipine 5mg OD, Low salt diet",
                notes="BP slightly elevated. Medication adjusted.",
                follow_up_date="2025-03-03",
                vital_signs={"temperature": "98.6°F", "blood_pressure": "145/95", "heart_rate": "82 bpm"},
            ),
            MedicalRecord(
                patient_id=pats[2].id, doctor_id=docs[0].id,
                diagnosis="Diabetes Type 2 Management", visit_date="2025-02-01",
                symptoms=["Increased thirst", "Fatigue"],
                prescription="Metformin 500mg BD, Insulin as prescribed",
                notes="Blood sugar needs better control. Diet plan discussed.",
                follow_up_date="2025-02-15",
                vital_signs={"temperature": "98.6°F", "blood_pressure": "130/85", "heart_rate": "75 bpm"},
            ),
            MedicalRecord(
                patient_id=pats[3].id, doctor_id=docs[2].id,
                diagnosis="Asthma", visit_date="2025-01-28",
                symptoms=["Shortness of breath", "Wheezing", "Chest tightness"],
                prescription="Salbutamol inhaler, Avoid triggers",
                notes="Asthma well-controlled. Keep inhaler available.",
                follow_up_date="2025-02-28",
                vital_signs={"temperature": "98.6°F", "blood_pressure": "120/78", "heart_rate": "80 bpm"},
            ),
        ]
        for r in recs: db.add(r)
        db.commit()
        print(f"  ✅ {len(recs)} medical records created")

        print("\n🎉 Database seeded!\n")
        print("Demo credentials:")
        print("  ahmed@pulseq.com   / doctor123")
        print("  sarah@pulseq.com   / doctor456")
        print("  hassan@pulseq.com  / doctor789\n")

    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed()