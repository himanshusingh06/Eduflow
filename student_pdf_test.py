#!/usr/bin/env python3
"""
Test Student PDF Q&A system
"""

import asyncio
import aiohttp

BASE_URL = "https://learnmate-ai-12.preview.emergentagent.com/api"

async def test_student_pdf_qa():
    """Test the student PDF Q&A system"""
    
    async with aiohttp.ClientSession() as session:
        # Login as student
        login_data = {
            "email": "emma.student@eduagent.com",
            "password": "student2024"
        }
        
        async with session.post(f"{BASE_URL}/auth/login", json=login_data) as response:
            if response.status != 200:
                print("❌ Failed to login")
                return
            
            login_result = await response.json()
            token = login_result["access_token"]
            print("✅ Successfully logged in")
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test 1: Get student PDFs
        async with session.get(f"{BASE_URL}/student/my-pdfs", headers=headers) as response:
            if response.status == 200:
                pdfs_result = await response.json()
                pdfs = pdfs_result.get("pdfs", [])
                print(f"✅ Retrieved {len(pdfs)} PDFs")
            else:
                print("❌ Failed to get PDFs")
                return
        
        # Test 2: Ask question with proper parameters
        # Since we don't have actual PDFs, let's test with a dummy material_id
        test_params = {
            "material_id": "test_material_123",
            "question": "What are the main topics covered in this material?"
        }
        
        async with session.post(f"{BASE_URL}/student/ask-my-pdf", params=test_params, headers=headers) as response:
            if response.status == 200:
                qa_result = await response.json()
                print("✅ PDF Q&A endpoint working")
                print(f"   Answer: {qa_result.get('answer', 'No answer')[:100]}...")
            else:
                error_text = await response.text()
                print(f"❌ PDF Q&A failed: {response.status}")
                print(f"   Error: {error_text}")
        
        # Test 3: Try with JSON body (to see if that works too)
        json_data = {
            "material_id": "test_material_123",
            "question": "Can you summarize the key concepts?"
        }
        
        async with session.post(f"{BASE_URL}/student/ask-my-pdf", json=json_data, headers=headers) as response:
            if response.status == 200:
                qa_result = await response.json()
                print("✅ PDF Q&A with JSON body also working")
                print(f"   Answer: {qa_result.get('answer', 'No answer')[:100]}...")
            else:
                error_text = await response.text()
                print(f"⚠️ PDF Q&A with JSON body failed: {response.status}")
                print(f"   Error: {error_text}")

if __name__ == "__main__":
    asyncio.run(test_student_pdf_qa())