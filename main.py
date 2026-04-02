# main.py
# Run with: python main.py
#
# IMPORTANT: bind to "localhost" (or 0.0.0.0), NOT "127.0.0.1".
# Flutter Web on Chrome treats 127.0.0.1 and localhost as different origins.
# Binding uvicorn to "localhost" makes it reachable as http://localhost:8000
# which matches what the Flutter frontend calls.

from api.index import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.index:app",
        host="localhost",   # <-- was "0.0.0.0", changed to "localhost" for Flutter Web
        port=8000,
        reload=True,
    )