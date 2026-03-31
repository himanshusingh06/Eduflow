#!/usr/bin/env python3
"""
Quick test for Gemini AI integration
"""

import asyncio
import aiohttp
import json

BASE_URL = "https://learnmate-ai-12.preview.emergentagent.com/api"

async def test_gemini_features():
    async with aiohttp.ClientSession() as session:
        # Login as student
        login_data = {
            "email": "alice.student@eduagent.com",
            "password": "student123"
        }
        
        async with session.post(f"{BASE_URL}/auth/login", json=login_data) as response:
            if response.status == 200:
                login_response = await response.json()
                token = login_response["access_token"]
                print("✅ Login successful")
            else:
                print("❌ Login failed")
                return
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test 1: Study content generation
        study_data = {
            "title": "AI Basics",
            "subject": "Computer Science",
            "grade_level": "Grade 12",
            "topic": "Artificial Intelligence",
            "tags": ["AI"]
        }
        
        async with session.post(f"{BASE_URL}/study/generate", json=study_data, headers=headers) as response:
            if response.status == 200:
                result = await response.json()
                print(f"✅ Study content generated: {len(result.get('content', ''))} chars")
            else:
                error = await response.text()
                print(f"❌ Study content failed: {response.status} - {error}")
        
        # Test 2: Quiz generation
        quiz_data = {
            "title": "AI Quiz",
            "subject": "Computer Science",
            "grade_level": "Grade 12",
            "topic": "Machine Learning",
            "num_questions": 3,
            "difficulty": "medium"
        }
        
        async with session.post(f"{BASE_URL}/quiz/generate", json=quiz_data, headers=headers) as response:
            if response.status == 200:
                result = await response.json()
                questions = result.get("questions", [])
                print(f"✅ Quiz generated: {len(questions)} questions")
                
                # Test quiz attempt
                if questions:
                    quiz_id = result["id"]
                    attempt_data = {"0": 0, "1": 1, "2": 0}  # String keys
                    
                    async with session.post(f"{BASE_URL}/quiz/{quiz_id}/attempt", json=attempt_data, headers=headers) as attempt_response:
                        if attempt_response.status == 200:
                            attempt_result = await attempt_response.json()
                            print(f"✅ Quiz attempt submitted: {attempt_result.get('percentage', 0)}%")
                            
                            # Test analysis
                            attempt_id = attempt_result["id"]
                            await asyncio.sleep(2)  # Wait for analysis
                            
                            async with session.get(f"{BASE_URL}/quiz/analysis/{attempt_id}", headers=headers) as analysis_response:
                                if analysis_response.status == 200:
                                    analysis = await analysis_response.json()
                                    print(f"✅ Quiz analysis generated: {len(analysis.get('insights', []))} insights")
                                else:
                                    error = await analysis_response.text()
                                    print(f"❌ Quiz analysis failed: {analysis_response.status} - {error}")
                        else:
                            error = await attempt_response.text()
                            print(f"❌ Quiz attempt failed: {attempt_response.status} - {error}")
            else:
                error = await response.text()
                print(f"❌ Quiz generation failed: {response.status} - {error}")
        
        # Test 3: AI Q&A
        qa_data = {
            "question": "What is machine learning?",
            "subject": "Computer Science"
        }
        
        async with session.post(f"{BASE_URL}/qa/ask", json=qa_data, headers=headers) as response:
            if response.status == 200:
                result = await response.json()
                answer = result.get("answer", "")
                print(f"✅ AI Q&A working: {len(answer)} chars")
            else:
                error = await response.text()
                print(f"❌ AI Q&A failed: {response.status} - {error}")

if __name__ == "__main__":
    asyncio.run(test_gemini_features())