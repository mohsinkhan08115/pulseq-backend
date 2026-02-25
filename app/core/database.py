import os
import json
import firebase_admin
from firebase_admin import credentials, db as rtdb

FIREBASE_DB_URL = "https://pulseq-6dfd0-default-rtdb.firebaseio.com"

def init_firebase():
    if not firebase_admin._apps:
        cred_json = os.environ.get("FIREBASE_CREDENTIALS")
        if cred_json:
            cred_dict = json.loads(cred_json)
            cred = credentials.Certificate(cred_dict)
        else:
            cred = credentials.Certificate("serviceAccountKey.json")
        firebase_admin.initialize_app(cred, {
            "databaseURL": FIREBASE_DB_URL
        })

init_firebase()

def get_ref(path: str):
    return rtdb.reference(path)