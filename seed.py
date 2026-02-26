"""
Run once to seed Firebase Realtime Database with demo data.
Usage: python seed.py
"""
import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import get_ref
from app.core.security import get_password_hash
import uuid

def seed():
    # Clear existing data
    get_ref("doctors").delete()
    get_ref("patients").delete()
    get_ref("doctor_patient").delete()
    get_ref("medical_records").delete()

    print("Seeding Firebase Realtime Database...")

    # Doctors
    doctors = [
        {"name": "Dr. Ahmed Khan",   "email": "ahmed@pulseq.com",
         "phone": "+92 300 1234567", "specialization": "Cardiologist",
         "hospital": "IDC Hospital", "hashed_password": get_password_hash("doctor123"),
         "is_active": True},
        {"name": "Dr. Sarah Ali",    "email": "sarah@pulseq.com",
         "phone": "+92 321 7654321", "specialization": "Pediatrician",
         "hospital": "City Hospital", "hashed_password": get_password_hash("doctor456"),
         "is_active": True},
        {"name": "Dr. Hassan Malik", "email": "hassan@pulseq.com",
         "phone": "+92 333 9876543", "specialization": "General Physician",
         "hospital": "Metro Medical", "hashed_password": get_password_hash("doctor789"),
         "is_active": True},
    ]
    doc_ids = []
    for d in doctors:
        did = str(uuid.uuid4())
        get_ref(f"doctors/{did}").set(d)
        doc_ids.append(did)
    print(f"  {len(doctors)} doctors created")

    # Patients
    patients = [
        {"name": "Hamda",        "email": "hamda@example.com",
         "phone": "+923000000001", "date_of_birth": "2004-03-09",
         "location": "Lahore",    "total_visits": 5, "last_visit": "2025-02-05",
         "medical_history_summary": "Regular checkups", "is_active": True,
         "patient_number": 1},
        {"name": "Ali Khan",     "email": "ali@example.com",
         "phone": "+923210000002", "date_of_birth": "1990-05-15",
         "location": "Karachi",   "total_visits": 8, "last_visit": "2025-02-03",
         "medical_history_summary": "Hypertension patient", "is_active": True,
         "patient_number": 2},
        {"name": "Fatima Ahmed", "email": "fatima@example.com",
         "phone": "+923330000003", "date_of_birth": "1985-08-20",
         "location": "Islamabad", "total_visits": 12, "last_visit": "2025-02-01",
         "medical_history_summary": "Diabetes Type 2", "is_active": True,
         "patient_number": 3},
        {"name": "Usman Raza",   "email": "usman@example.com",
         "phone": "+923450000004", "date_of_birth": "1995-12-10",
         "location": "Lahore",    "total_visits": 3, "last_visit": "2025-01-28",
         "medical_history_summary": "Asthma patient", "is_active": True,
         "patient_number": 4},
    ]
    pat_ids = []
    for p in patients:
        pid = str(uuid.uuid4())
        get_ref(f"patients/{pid}").set(p)
        pat_ids.append(pid)
    print(f"  {len(patients)} patients created")

    # Doctor-patient links
    links = [
        (doc_ids[0], pat_ids[0]), (doc_ids[0], pat_ids[1]),
        (doc_ids[0], pat_ids[2]), (doc_ids[1], pat_ids[0]),
        (doc_ids[1], pat_ids[3]), (doc_ids[2], pat_ids[3]),
        (doc_ids[2], pat_ids[2]),
    ]
    for did, pid in links:
        get_ref(f"doctor_patient/{did}_{pid}").set({
            "doctor_id": did, "patient_id": pid
        })
    print(f"  {len(links)} doctor-patient links created")

    # Medical Records
    records = [
        # ── Hamda (5 records) ──────────────────────────────────────
        {"patient_id": pat_ids[0], "doctor_id": doc_ids[0],
         "diagnosis": "Fever and Flu", "visit_date": "2025-02-05",
         "symptoms": ["Fever", "Cough", "Headache"],
         "prescription": "Paracetamol 500mg TID for 5 days",
         "notes": "Rest for 3 days. Stay hydrated.",
         "follow_up_date": "2025-02-12",
         "vital_signs": {"temperature": "101F", "blood_pressure": "120/80", "pulse": "88 bpm"}},

        {"patient_id": pat_ids[0], "doctor_id": doc_ids[0],
         "diagnosis": "Seasonal Allergies", "visit_date": "2024-11-10",
         "symptoms": ["Sneezing", "Runny nose", "Itchy eyes"],
         "prescription": "Cetirizine 10mg OD for 7 days",
         "notes": "Avoid dust and pollen. Use mask outdoors.",
         "follow_up_date": "2024-11-20",
         "vital_signs": {"temperature": "98.6F", "blood_pressure": "118/76", "pulse": "80 bpm"}},

        {"patient_id": pat_ids[0], "doctor_id": doc_ids[1],
         "diagnosis": "Vitamin D Deficiency", "visit_date": "2024-08-15",
         "symptoms": ["Fatigue", "Bone pain", "Muscle weakness"],
         "prescription": "Vitamin D3 50000 IU weekly for 8 weeks",
         "notes": "Sun exposure recommended. Repeat test after 2 months.",
         "follow_up_date": "2024-10-15",
         "vital_signs": {"temperature": "98.4F", "blood_pressure": "115/75", "pulse": "76 bpm"}},

        {"patient_id": pat_ids[0], "doctor_id": doc_ids[0],
         "diagnosis": "Gastritis", "visit_date": "2024-05-20",
         "symptoms": ["Stomach pain", "Nausea", "Bloating"],
         "prescription": "Omeprazole 20mg OD before breakfast for 2 weeks",
         "notes": "Avoid spicy food and soda. Eat small meals.",
         "follow_up_date": "2024-06-03",
         "vital_signs": {"temperature": "98.6F", "blood_pressure": "120/80", "pulse": "82 bpm"}},

        {"patient_id": pat_ids[0], "doctor_id": doc_ids[1],
         "diagnosis": "Iron Deficiency Anemia", "visit_date": "2024-02-10",
         "symptoms": ["Fatigue", "Pale skin", "Dizziness"],
         "prescription": "Ferrous sulfate 200mg BD for 3 months",
         "notes": "Increase iron-rich foods. Take with Vitamin C.",
         "follow_up_date": "2024-05-10",
         "vital_signs": {"temperature": "98.2F", "blood_pressure": "110/70", "pulse": "92 bpm"}},

        # ── Ali Khan (3 records) ───────────────────────────────────
        {"patient_id": pat_ids[1], "doctor_id": doc_ids[0],
         "diagnosis": "Hypertension Follow-up", "visit_date": "2025-02-03",
         "symptoms": ["Elevated BP", "Dizziness"],
         "prescription": "Amlodipine 5mg OD",
         "notes": "BP slightly elevated. Reduce salt intake.",
         "follow_up_date": "2025-03-03",
         "vital_signs": {"temperature": "98.6F", "blood_pressure": "145/95", "pulse": "85 bpm"}},

        {"patient_id": pat_ids[1], "doctor_id": doc_ids[0],
         "diagnosis": "Hypertension Initial Diagnosis", "visit_date": "2024-10-10",
         "symptoms": ["Headache", "Blurred vision", "High BP"],
         "prescription": "Lisinopril 10mg OD",
         "notes": "Lifestyle changes advised. Regular BP monitoring.",
         "follow_up_date": "2024-11-10",
         "vital_signs": {"temperature": "98.6F", "blood_pressure": "160/100", "pulse": "90 bpm"}},

        {"patient_id": pat_ids[1], "doctor_id": doc_ids[0],
         "diagnosis": "Chest Pain Evaluation", "visit_date": "2024-06-15",
         "symptoms": ["Chest pain", "Shortness of breath"],
         "prescription": "ECG ordered. Aspirin 75mg OD",
         "notes": "ECG normal. Stress test scheduled.",
         "follow_up_date": "2024-06-22",
         "vital_signs": {"temperature": "98.6F", "blood_pressure": "150/95", "pulse": "95 bpm"}},

        # ── Fatima Ahmed (3 records) ───────────────────────────────
        {"patient_id": pat_ids[2], "doctor_id": doc_ids[0],
         "diagnosis": "Diabetes Type 2", "visit_date": "2025-02-01",
         "symptoms": ["Increased thirst", "Fatigue"],
         "prescription": "Metformin 500mg BD",
         "notes": "Diet plan discussed. HbA1c target < 7%.",
         "follow_up_date": "2025-02-15",
         "vital_signs": {"temperature": "98.6F", "blood_pressure": "130/85", "pulse": "80 bpm"}},

        {"patient_id": pat_ids[2], "doctor_id": doc_ids[2],
         "diagnosis": "Diabetes Type 2 - Quarterly Review", "visit_date": "2024-11-01",
         "symptoms": ["Fatigue", "Frequent urination"],
         "prescription": "Metformin 1000mg BD. Glipizide 5mg OD",
         "notes": "HbA1c slightly elevated. Increase medication.",
         "follow_up_date": "2025-02-01",
         "vital_signs": {"temperature": "98.6F", "blood_pressure": "135/88", "pulse": "78 bpm"}},

        {"patient_id": pat_ids[2], "doctor_id": doc_ids[0],
         "diagnosis": "Diabetic Foot Check", "visit_date": "2024-07-20",
         "symptoms": ["Numbness in feet", "Tingling"],
         "prescription": "Gabapentin 300mg TID. Continue Metformin.",
         "notes": "Neuropathy signs. Daily foot inspection advised.",
         "follow_up_date": "2024-10-20",
         "vital_signs": {"temperature": "98.6F", "blood_pressure": "128/82", "pulse": "76 bpm"}},

        # ── Usman Raza (3 records) ─────────────────────────────────
        {"patient_id": pat_ids[3], "doctor_id": doc_ids[2],
         "diagnosis": "Asthma", "visit_date": "2025-01-28",
         "symptoms": ["Shortness of breath", "Wheezing"],
         "prescription": "Salbutamol inhaler PRN. Budesonide inhaler BD.",
         "notes": "Keep inhaler available at all times.",
         "follow_up_date": "2025-02-28",
         "vital_signs": {"temperature": "98.6F", "blood_pressure": "120/78", "pulse": "88 bpm"}},

        {"patient_id": pat_ids[3], "doctor_id": doc_ids[1],
         "diagnosis": "Asthma Exacerbation", "visit_date": "2024-09-05",
         "symptoms": ["Severe wheezing", "Chest tightness", "Cough"],
         "prescription": "Prednisolone 30mg OD for 5 days. Salbutamol nebulization.",
         "notes": "Avoid triggers. Use peak flow meter daily.",
         "follow_up_date": "2024-09-12",
         "vital_signs": {"temperature": "99.0F", "blood_pressure": "125/80", "pulse": "100 bpm"}},

        {"patient_id": pat_ids[3], "doctor_id": doc_ids[2],
         "diagnosis": "Asthma Initial Diagnosis", "visit_date": "2024-03-15",
         "symptoms": ["Recurring cough", "Breathlessness at night"],
         "prescription": "Salbutamol inhaler PRN.",
         "notes": "Spirometry done. Mild asthma confirmed.",
         "follow_up_date": "2024-06-15",
         "vital_signs": {"temperature": "98.6F", "blood_pressure": "118/76", "pulse": "84 bpm"}},
    ]

    for r in records:
        rid = str(uuid.uuid4())
        get_ref(f"medical_records/{rid}").set(r)
    print(f"  {len(records)} medical records created")

    print("\nFirebase Realtime Database seeded successfully!")
    print("\nDemo credentials:")
    print("  ahmed@pulseq.com  / doctor123")
    print("  sarah@pulseq.com  / doctor456")
    print("  hassan@pulseq.com / doctor789")
    print("\nPatient numbers:")
    print("  1 = Hamda        | +923000000001  (5 records)")
    print("  2 = Ali Khan     | +923210000002  (3 records)")
    print("  3 = Fatima Ahmed | +923330000003  (3 records)")
    print("  4 = Usman Raza   | +923450000004  (3 records)")

if __name__ == "__main__":
    seed()