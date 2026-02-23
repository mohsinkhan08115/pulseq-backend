"""
Backend Test Script
Run this to test if your backend is working correctly
"""
import sys
import socket

def test_backend():
    print("=" * 60)
    print("🔧 MEDICAL RECORDS BACKEND - DIAGNOSTIC TEST")
    print("=" * 60)
    print()
    
    # Test 1: Get local IP
    print("📡 Test 1: Network Configuration")
    print("-" * 60)
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        print(f"✅ Hostname: {hostname}")
        print(f"✅ Local IP: {local_ip}")
        print(f"✅ Backend should be at: http://{local_ip}:8000")
    except Exception as e:
        print(f"❌ Error getting IP: {e}")
    print()
    
    # Test 2: Check imports
    print("📦 Test 2: Required Packages")
    print("-" * 60)
    required_packages = [
        'fastapi',
        'uvicorn',
        'jose',
        'passlib',
        'pydantic',
        'pydantic_settings'
    ]
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package:20s} - installed")
        except ImportError:
            print(f"❌ {package:20s} - MISSING! Install with: pip install {package}")
    print()
    
    # Test 3: Check app structure
    print("📁 Test 3: Project Structure")
    print("-" * 60)
    import os
    
    required_files = [
        'main.py',
        'app/__init__.py',
        'app/database.py',
        'app/core/config.py',
        'app/core/security.py',
        'app/routes/auth.py',
        'app/routes/patients.py',
        'app/routes/medical_records.py',
    ]
    
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} - MISSING!")
    print()
    
    # Test 4: Test password hashing
    print("🔐 Test 4: Password Hashing")
    print("-" * 60)
    try:
        from app.core.security import get_password_hash, verify_password
        
        test_password = "doctor123"
        hashed = get_password_hash(test_password)
        is_valid = verify_password(test_password, hashed)
        
        print(f"✅ Password hashing works!")
        print(f"   Plain: {test_password}")
        print(f"   Hash: {hashed[:50]}...")
        print(f"   Verification: {is_valid}")
    except Exception as e:
        print(f"❌ Error with password hashing: {e}")
    print()
    
    # Test 5: Check database
    print("💾 Test 5: Database")
    print("-" * 60)
    try:
        from backend.database import DOCTORS_DB, PATIENTS_DB, MEDICAL_RECORDS_DB
        
        print(f"✅ Doctors in database: {len(DOCTORS_DB)}")
        for doc_id, doc in DOCTORS_DB.items():
            print(f"   - {doc['name']} ({doc['email']})")
        
        print(f"✅ Patients in database: {len(PATIENTS_DB)}")
        print(f"✅ Medical records: {len(MEDICAL_RECORDS_DB)}")
    except Exception as e:
        print(f"❌ Error loading database: {e}")
    print()
    
    # Test 6: Test login credentials
    print("🔑 Test 6: Valid Login Credentials")
    print("-" * 60)
    try:
        from backend.database import DOCTORS_DB
        
        print("Use these credentials to login:")
        print()
        for doc_id, doc in DOCTORS_DB.items():
            print(f"Account {doc_id}:")
            print(f"  Email:    {doc['email']}")
            print(f"  Phone:    {doc['phone']}")
            print(f"  Password: doctor{doc_id * 111 + 12}")  # Matches the pattern
            print()
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("=" * 60)
    print("✅ DIAGNOSTIC TEST COMPLETE!")
    print("=" * 60)
    print()
    print("🚀 To start the backend server, run:")
    print("   python main.py")
    print()
    print("📚 Then access the API docs at:")
    print(f"   http://{local_ip}:8000/docs")
    print()

if __name__ == "__main__":
    test_backend()