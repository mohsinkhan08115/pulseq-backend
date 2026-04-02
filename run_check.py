#!/usr/bin/env python3
"""
run_check.py  —  Quick connectivity & CORS diagnostic for PulseQ backend.
Usage:  python run_check.py
"""
import sys
import socket
import urllib.request
import urllib.error
import json


BASE = "http://localhost:8000"
PATIENT_LOGIN = f"{BASE}/patient-auth/login"
HEALTH = f"{BASE}/health"


def section(title: str):
    print(f"\n{'─' * 55}")
    print(f"  {title}")
    print(f"{'─' * 55}")


def ok(msg):  print(f"  ✅  {msg}")
def fail(msg): print(f"  ❌  {msg}")
def info(msg): print(f"  ℹ️   {msg}")


# ── 1. Port check ─────────────────────────────────────────────────────────────
section("1 · Is port 8000 open on localhost?")
try:
    with socket.create_connection(("localhost", 8000), timeout=2):
        ok("Port 8000 is OPEN — something is listening")
except OSError:
    fail("Port 8000 is CLOSED — backend is NOT running")
    info("Start it with:  python main.py")
    sys.exit(1)


# ── 2. Health endpoint ────────────────────────────────────────────────────────
section("2 · GET /health")
try:
    req = urllib.request.Request(HEALTH)
    with urllib.request.urlopen(req, timeout=5) as r:
        body = json.loads(r.read())
        ok(f"Response: {body}")
except Exception as e:
    fail(f"Could not reach /health — {e}")


# ── 3. CORS preflight (OPTIONS) ────────────────────────────────────────────────
section("3 · OPTIONS preflight (simulates Flutter Web browser)")
try:
    req = urllib.request.Request(
        PATIENT_LOGIN,
        method="OPTIONS",
        headers={
            "Origin": "http://localhost:63925",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type,Authorization",
        },
    )
    with urllib.request.urlopen(req, timeout=5) as r:
        acao = r.headers.get("Access-Control-Allow-Origin", "MISSING")
        acam = r.headers.get("Access-Control-Allow-Methods", "MISSING")
        ok(f"CORS OK  —  Allow-Origin: {acao}  |  Allow-Methods: {acam}")
except urllib.error.HTTPError as e:
    if e.code in (200, 204):
        ok(f"Preflight returned {e.code} — CORS headers present")
    else:
        fail(f"Preflight failed with HTTP {e.code}: {e.reason}")
except Exception as e:
    fail(f"Preflight error: {e}")


# ── 4. POST /patient-auth/login (real credential test) ───────────────────────
section("4 · POST /patient-auth/login  (Hamda / doctor123)")
payload = json.dumps({"phone": "+923000000001", "password": "doctor123"}).encode()
try:
    req = urllib.request.Request(
        PATIENT_LOGIN,
        data=payload,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Origin": "http://localhost:63925",
        },
    )
    with urllib.request.urlopen(req, timeout=5) as r:
        body = json.loads(r.read())
        ok(f"Login success — patient: {body.get('patient', {}).get('name')}")
        ok(f"Token prefix: {body.get('access_token', '')[:30]}…")
except urllib.error.HTTPError as e:
    body = e.read().decode()
    fail(f"HTTP {e.code} — {body}")
except Exception as e:
    fail(f"Login error: {e}")


# ── Summary ───────────────────────────────────────────────────────────────────
section("Summary & next steps")
info("If all checks passed, the backend is healthy.")
info("In Flutter, make sure api_constants.dart has:")
info('    static const String baseUrl = "http://localhost:8000";')
info("Then run Flutter Web with:")
info("    flutter run -d chrome --web-port 63925")
print()