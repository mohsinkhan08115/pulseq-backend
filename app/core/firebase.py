import os
import json
import firebase_admin
from firebase_admin import credentials, db

FIREBASE_DB_URL = "https://pulseq-6dfd0-default-rtdb.firebaseio.com"

def init_firebase():
    if not firebase_admin._apps:
        cred_json = os.environ.get("FIREBASE_CREDENTIALS")
        if cred_json:
            # Single JSON string (old method)
            cred_dict = json.loads(cred_json)
            cred = credentials.Certificate(cred_dict)
        elif os.environ.get("FIREBASE_TYPE"):
            # Individual environment variables
            private_key = os.environ.get("FIREBASE_PRIVATE_KEY", "")
            # Fix escaped newlines
            private_key = private_key.replace("\\n", "\n")
            cred_dict = {
                "type": os.environ.get("FIREBASE_TYPE"),
                "project_id": os.environ.get("FIREBASE_PROJECT_ID"),
                "private_key_id": os.environ.get("FIREBASE_PRIVATE_KEY_ID"),
                "private_key": private_key,
                "client_email": os.environ.get("FIREBASE_CLIENT_EMAIL"),
                "client_id": os.environ.get("FIREBASE_CLIENT_ID"),
                "auth_uri": os.environ.get("FIREBASE_AUTH_URI", "https://accounts.google.com/o/oauth2/auth"),
                "token_uri": os.environ.get("FIREBASE_TOKEN_URI", "https://oauth2.googleapis.com/token"),
                "auth_provider_x509_cert_url": os.environ.get("FIREBASE_AUTH_PROVIDER_CERT_URL", "https://www.googleapis.com/oauth2/v1/certs"),
                "client_x509_cert_url": os.environ.get("FIREBASE_CLIENT_CERT_URL"),
                "universe_domain": "googleapis.com"
            }
            cred = credentials.Certificate(cred_dict)
        else:
            # Local development
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