# app/core/database.py
import os
import json
import firebase_admin
from firebase_admin import credentials, db

FIREBASE_DB_URL = "https://pulseq-6dfd0-default-rtdb.firebaseio.com"


def init_firebase():
    if firebase_admin._apps:
        return  # Already initialized

    cred_json = os.environ.get("FIREBASE_CREDENTIALS")

    if cred_json:
        # ── Vercel: from environment variable ─────────────────────────
        try:
            # Strip any surrounding whitespace or quotes
            cred_json = cred_json.strip().strip("'\"")
            cred_dict = json.loads(cred_json)
            cred = credentials.Certificate(cred_dict)
        except json.JSONDecodeError as e:
            raise RuntimeError(
                f"FIREBASE_CREDENTIALS is not valid JSON: {e}\n"
                f"First 100 chars: {cred_json[:100]}"
            )
    elif os.path.exists("serviceAccountKey.json"):
        # ── Local development: from file ───────────────────────────────
        cred = credentials.Certificate("serviceAccountKey.json")
    else:
        raise RuntimeError(
            "Firebase credentials not found!\n"
            "Set FIREBASE_CREDENTIALS environment variable on Vercel,\n"
            "or place serviceAccountKey.json in project root for local dev."
        )

    firebase_admin.initialize_app(cred, {
        "databaseURL": FIREBASE_DB_URL
    })


# Initialize on import
init_firebase()


def get_ref(path: str):
    return db.reference(path)