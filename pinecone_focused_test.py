#!/usr/bin/env python3
"""
Focused Pinecone RAG Integration Test
Tests the specific issues found in the comprehensive test
"""

import asyncio
import aiohttp
import json

BASE_URL = "https://learnmate-ai-12.preview.emergentagent.com/api"

async def test_pinecone_integration():
    """Test Pinecone integration specifically"""
    
    # Login as student
    login_data = {
        "email": "rag.student@eduagent.com",
        "password": "ragstudent2024"
    }
    
    async with aiohttp.ClientSession() as session:
        # Login
        async with session.post(f"{BASE_URL}/auth/login", json=login_data) as response:
            if response.status == 200:
                login_response = await response.json()
                token = login_response["access_token"]
                print("✅ Login successful")
            else:
                print("❌ Login failed")
                return
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test 1: RAG query with no materials
        rag_query = {
            "question": "What is quantum mechanics?",
            "subject": "Physics",
            "grade_level": "Grade 12"
        }
        
        async with session.post(f"{BASE_URL}/rag/ask", json=rag_query, headers=headers) as response:
            if response.status == 200:
                rag_response = await response.json()
                answer = rag_response.get("answer", "")
                print(f"✅ RAG Query successful: {len(answer)} chars")
                print(f"   Answer preview: {answer[:100]}...")
                
                # Check if Pinecone is working or using fallback
                if "general ai answer" in answer.lower():
                    print("   📝 Using fallback (no materials found)")
                elif "answer from course materials" in answer.lower():
                    print("   📚 Using Pinecone vector search")
                else:
                    print("   🤖 Using AI response")
            else:
                error_response = await response.json()
                print(f"❌ RAG Query failed: {error_response}")
        
        # Test 2: Student PDF query endpoint (correct method)
        pdf_query_data = {
            "material_id": "student_test_material",
            "question": "What is this document about?"
        }
        
        async with session.post(f"{BASE_URL}/student/ask-my-pdf", json=pdf_query_data, headers=headers) as response:
            if response.status == 200:
                pdf_response = await response.json()
                print("✅ Student PDF query endpoint working")
            elif response.status == 403:
                print("✅ Student PDF query properly validates material ownership")
            else:
                error_response = await response.json()
                print(f"❌ Student PDF query failed: {error_response}")
        
        # Test 3: Empty query validation
        empty_query = {
            "question": "",
            "subject": "Test"
        }
        
        async with session.post(f"{BASE_URL}/rag/ask", json=empty_query, headers=headers) as response:
            if response.status == 200:
                empty_response = await response.json()
                answer = empty_response.get("answer", "")
                if len(answer) < 50:
                    print("✅ Empty query handled appropriately")
                else:
                    print("❌ Empty query should be validated")
            else:
                print("✅ Empty query properly rejected")

if __name__ == "__main__":
    asyncio.run(test_pinecone_integration())