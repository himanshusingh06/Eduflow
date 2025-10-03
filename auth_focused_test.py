#!/usr/bin/env python3
"""
Focused Authentication Testing for EduAgent
Tests specific authentication scenarios as requested
"""

import asyncio
import aiohttp
import json
from datetime import datetime

BASE_URL = "https://learnmate-ai-12.preview.emergentagent.com/api"

async def test_authentication_scenarios():
    """Test specific authentication scenarios"""
    
    async with aiohttp.ClientSession() as session:
        print("🔐 FOCUSED AUTHENTICATION TESTING")
        print("=" * 50)
        
        # Test 1: Register new user
        print("\n1. Testing Registration with new user...")
        new_user = {
            "email": f"test.{datetime.now().strftime('%Y%m%d%H%M%S')}@eduagent.com",
            "password": "testpass123",
            "name": "Test User",
            "role": "student",
            "phone": "+1234567890"
        }
        
        async with session.post(f"{BASE_URL}/auth/register", json=new_user) as resp:
            if resp.status == 200:
                data = await resp.json()
                print(f"✅ Registration successful: {data.get('user', {}).get('name')}")
                print(f"   Token length: {len(data.get('access_token', ''))}")
                new_user_token = data.get('access_token')
                new_user_id = data.get('user', {}).get('id')
            else:
                error = await resp.text()
                print(f"❌ Registration failed: {error}")
                return
        
        # Test 2: Login with valid credentials
        print("\n2. Testing Login with valid credentials...")
        login_data = {"email": new_user["email"], "password": new_user["password"]}
        
        async with session.post(f"{BASE_URL}/auth/login", json=login_data) as resp:
            if resp.status == 200:
                data = await resp.json()
                print(f"✅ Login successful: {data.get('user', {}).get('name')}")
                login_token = data.get('access_token')
                print(f"   Token same as registration: {login_token == new_user_token}")
            else:
                error = await resp.text()
                print(f"❌ Login failed: {error}")
                return
        
        # Test 3: Login with invalid credentials
        print("\n3. Testing Login with invalid credentials...")
        invalid_login = {"email": new_user["email"], "password": "wrongpassword"}
        
        async with session.post(f"{BASE_URL}/auth/login", json=invalid_login) as resp:
            if resp.status == 401:
                print("✅ Invalid credentials correctly rejected")
            else:
                error = await resp.text()
                print(f"❌ Should reject invalid credentials: {error}")
        
        # Test 4: Access protected route with valid token
        print("\n4. Testing protected route /auth/me with valid token...")
        headers = {"Authorization": f"Bearer {login_token}"}
        
        async with session.get(f"{BASE_URL}/auth/me", headers=headers) as resp:
            if resp.status == 200:
                data = await resp.json()
                print(f"✅ Protected route access successful: {data.get('name')}")
                print(f"   User ID: {data.get('id')}")
                print(f"   Role: {data.get('role')}")
            else:
                error = await resp.text()
                print(f"❌ Protected route access failed: {error}")
        
        # Test 5: Access protected route with invalid token
        print("\n5. Testing protected route with invalid token...")
        invalid_headers = {"Authorization": "Bearer invalid.token.here"}
        
        async with session.get(f"{BASE_URL}/auth/me", headers=invalid_headers) as resp:
            if resp.status == 401:
                print("✅ Invalid token correctly rejected")
            else:
                error = await resp.text()
                print(f"❌ Should reject invalid token: {error}")
        
        # Test 6: Access protected route without token
        print("\n6. Testing protected route without token...")
        
        async with session.get(f"{BASE_URL}/auth/me") as resp:
            if resp.status == 403:
                print("✅ Missing token correctly rejected")
            else:
                error = await resp.text()
                print(f"❌ Should require token: {error}")
        
        # Test 7: Register duplicate email
        print("\n7. Testing registration with duplicate email...")
        
        async with session.post(f"{BASE_URL}/auth/register", json=new_user) as resp:
            if resp.status == 400:
                error_data = await resp.json()
                if "already registered" in str(error_data).lower():
                    print("✅ Duplicate email correctly rejected")
                else:
                    print(f"❌ Wrong error message: {error_data}")
            else:
                print(f"❌ Should reject duplicate email: {resp.status}")
        
        # Test 8: Test role-based access
        print("\n8. Testing role-based access controls...")
        
        # Create teacher user
        teacher_user = {
            "email": f"teacher.{datetime.now().strftime('%Y%m%d%H%M%S')}@eduagent.com",
            "password": "teacherpass123",
            "name": "Test Teacher",
            "role": "teacher",
            "phone": "+1234567891"
        }
        
        async with session.post(f"{BASE_URL}/auth/register", json=teacher_user) as resp:
            if resp.status == 200:
                data = await resp.json()
                teacher_token = data.get('access_token')
                print(f"✅ Teacher registered: {data.get('user', {}).get('name')}")
            else:
                error = await resp.text()
                print(f"❌ Teacher registration failed: {error}")
                return
        
        # Test student accessing student endpoint
        student_headers = {"Authorization": f"Bearer {login_token}"}
        async with session.get(f"{BASE_URL}/student/profile", headers=student_headers) as resp:
            if resp.status == 200:
                print("✅ Student can access student endpoints")
            else:
                error = await resp.text()
                print(f"❌ Student should access student endpoints: {error}")
        
        # Test teacher accessing teacher endpoint
        teacher_headers = {"Authorization": f"Bearer {teacher_token}"}
        async with session.get(f"{BASE_URL}/teacher/my-materials", headers=teacher_headers) as resp:
            if resp.status == 200:
                print("✅ Teacher can access teacher endpoints")
            else:
                error = await resp.text()
                print(f"❌ Teacher should access teacher endpoints: {error}")
        
        # Test cross-role access (student -> teacher endpoint)
        async with session.get(f"{BASE_URL}/teacher/my-materials", headers=student_headers) as resp:
            if resp.status == 403:
                print("✅ Student correctly blocked from teacher endpoints")
            else:
                error = await resp.text()
                print(f"❌ Student should be blocked from teacher endpoints: {resp.status} - {error}")
        
        # Test cross-role access (teacher -> student endpoint)
        async with session.get(f"{BASE_URL}/student/profile", headers=teacher_headers) as resp:
            if resp.status == 403:
                print("✅ Teacher correctly blocked from student endpoints")
            else:
                data = await resp.text()
                print(f"❌ Teacher should be blocked from student endpoints: {resp.status} - {data}")
        
        print("\n" + "=" * 50)
        print("🎯 AUTHENTICATION TESTING COMPLETE")

if __name__ == "__main__":
    asyncio.run(test_authentication_scenarios())