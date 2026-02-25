import os
import json
import firebase_admin
from firebase_admin import credentials, db

FIREBASE_DB_URL = "https://pulseq-6dfd0-default-rtdb.firebaseio.com"


def init_firebase():
    if not firebase_admin._apps:
        cred_json = os.environ.get("FIREBASE_CREDENTIALS")

        if cred_json:
            # When deployed on Vercel (using environment variable)
            cred_dict = json.loads(cred_json)
            cred = credentials.Certificate(cred_dict)
        else:
            # When running locally (using serviceAccountKey.json file)
            cred = credentials.Certificate("serviceAccountKey.json")

        firebase_admin.initialize_app(cred, {
            "databaseURL": FIREBASE_DB_URL
        })


# Initialize Firebase once
init_firebase()


def get_ref(path: str):
    """
    Get a reference to a Firebase Realtime Database path
    Example: get_ref("users").get()
    """
    return db.reference(path)