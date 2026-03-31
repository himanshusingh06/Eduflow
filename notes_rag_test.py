#!/usr/bin/env python3
"""
Test Notes Management and RAG System
"""

import asyncio
import aiohttp
import json

BASE_URL = "https://learnmate-ai-12.preview.emergentagent.com/api"

async def test_notes_and_rag():
    async with aiohttp.ClientSession() as session:
        # Login as student
        login_data = {
            "email": "alice.student@eduagent.com",
            "password": "student123"
        }
        
        async with session.post(f"{BASE_URL}/auth/login", json=login_data) as response:
            if response.status == 200:
                login_response = await response.json()
                student_token = login_response["access_token"]
                print("✅ Student login successful")
            else:
                print("❌ Student login failed")
                return
        
        # Login as teacher
        teacher_login = {
            "email": "bob.teacher@eduagent.com",
            "password": "teacher123"
        }
        
        async with session.post(f"{BASE_URL}/auth/login", json=teacher_login) as response:
            if response.status == 200:
                login_response = await response.json()
                teacher_token = login_response["access_token"]
                print("✅ Teacher login successful")
            else:
                print("❌ Teacher login failed")
                return
        
        student_headers = {"Authorization": f"Bearer {student_token}"}
        teacher_headers = {"Authorization": f"Bearer {teacher_token}"}
        
        # Test 1: Create Note
        note_data = {
            "title": "Machine Learning Fundamentals",
            "content": "Machine learning is a method of data analysis that automates analytical model building. It is a branch of artificial intelligence based on the idea that systems can learn from data, identify patterns and make decisions with minimal human intervention. Key types include supervised learning, unsupervised learning, and reinforcement learning.",
            "subject": "Computer Science",
            "tags": ["AI", "ML", "data science"]
        }
        
        async with session.post(f"{BASE_URL}/notes/create", json=note_data, headers=student_headers) as response:
            if response.status == 200:
                result = await response.json()
                print(f"✅ Note created: {result.get('id', 'unknown')}")
            else:
                error = await response.text()
                print(f"❌ Note creation failed: {response.status} - {error}")
        
        # Test 2: Get My Notes
        async with session.get(f"{BASE_URL}/notes/my-notes", headers=student_headers) as response:
            if response.status == 200:
                result = await response.json()
                notes = result.get("notes", [])
                print(f"✅ Retrieved {len(notes)} notes")
            else:
                error = await response.text()
                print(f"❌ Get notes failed: {response.status} - {error}")
        
        # Test 3: Note Summarization - Brief
        summary_data = {
            "note_content": note_data["content"],
            "summary_type": "brief"
        }
        
        async with session.post(f"{BASE_URL}/notes/summarize", json=summary_data, headers=student_headers) as response:
            if response.status == 200:
                result = await response.json()
                summary = result.get("summary", "")
                print(f"✅ Brief summary generated: {len(summary)} chars")
            else:
                error = await response.text()
                print(f"❌ Brief summary failed: {response.status} - {error}")
        
        # Test 4: Note Summarization - Detailed
        summary_data["summary_type"] = "detailed"
        async with session.post(f"{BASE_URL}/notes/summarize", json=summary_data, headers=student_headers) as response:
            if response.status == 200:
                result = await response.json()
                summary = result.get("summary", "")
                print(f"✅ Detailed summary generated: {len(summary)} chars")
            else:
                error = await response.text()
                print(f"❌ Detailed summary failed: {response.status} - {error}")
        
        # Test 5: Note Summarization - Key Points
        summary_data["summary_type"] = "key_points"
        async with session.post(f"{BASE_URL}/notes/summarize", json=summary_data, headers=student_headers) as response:
            if response.status == 200:
                result = await response.json()
                summary = result.get("summary", "")
                print(f"✅ Key points generated: {len(summary)} chars")
            else:
                error = await response.text()
                print(f"❌ Key points failed: {response.status} - {error}")
        
        # Test 6: RAG Query (should handle empty materials gracefully)
        rag_query = {
            "question": "What are the main types of machine learning?",
            "subject": "Computer Science",
            "grade_level": "Grade 12"
        }
        
        async with session.post(f"{BASE_URL}/rag/ask", json=rag_query, headers=student_headers) as response:
            if response.status == 200:
                result = await response.json()
                answer = result.get("answer", "")
                print(f"✅ RAG query handled: {len(answer)} chars")
            else:
                error = await response.text()
                print(f"❌ RAG query failed: {response.status} - {error}")
        
        # Test 7: Teacher Materials List
        async with session.get(f"{BASE_URL}/teacher/my-materials", headers=teacher_headers) as response:
            if response.status == 200:
                result = await response.json()
                materials = result.get("materials", [])
                print(f"✅ Teacher materials retrieved: {len(materials)} materials")
            else:
                error = await response.text()
                print(f"❌ Teacher materials failed: {response.status} - {error}")

if __name__ == "__main__":
    asyncio.run(test_notes_and_rag())