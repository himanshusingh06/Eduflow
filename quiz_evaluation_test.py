#!/usr/bin/env python3
"""
Focused test for Quiz Evaluation & Email System
"""

import asyncio
import aiohttp
import json

BASE_URL = "https://learnmate-ai-12.preview.emergentagent.com/api"

async def test_quiz_evaluation():
    """Test the complete quiz evaluation flow"""
    
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
        
        # Step 1: Generate a dynamic quiz
        quiz_request = {
            "subject": "Mathematics",
            "topic": "Quadratic Equations",
            "difficulty": "medium",
            "num_questions": 7,
            "grade_level": "Grade 10"
        }
        
        async with session.post(f"{BASE_URL}/quiz/generate-dynamic", json=quiz_request, headers=headers) as response:
            if response.status != 200:
                print("❌ Failed to generate quiz")
                return
            
            quiz_result = await response.json()
            quiz_id = quiz_result["quiz"]["id"]
            quiz_data = quiz_result["quiz"]
            print(f"✅ Generated quiz: {quiz_id}")
            print(f"   Title: {quiz_data['quiz_title']}")
            print(f"   Questions: {len(quiz_data['questions'])}")
        
        # Step 2: Prepare student answers (mix of correct and incorrect)
        student_answers = {}
        questions = quiz_data["questions"]
        
        for i, question in enumerate(questions):
            if i < len(questions) // 2:
                # First half - correct answers
                student_answers[str(i)] = question["correct_answer"]
            else:
                # Second half - incorrect answers
                options = list(question["options"].keys())
                correct = question["correct_answer"]
                # Pick a different option
                incorrect_options = [opt for opt in options if opt != correct]
                student_answers[str(i)] = incorrect_options[0] if incorrect_options else correct
        
        print(f"✅ Prepared answers: {len(student_answers)} responses")
        
        # Step 3: Submit quiz for evaluation
        async with session.post(f"{BASE_URL}/quiz/submit-dynamic/{quiz_id}", json=student_answers, headers=headers) as response:
            if response.status != 200:
                print(f"❌ Failed to submit quiz: {response.status}")
                error_text = await response.text()
                print(f"   Error: {error_text}")
                return
            
            evaluation_result = await response.json()
            print("✅ Quiz evaluation completed!")
            
            if "evaluation" in evaluation_result:
                eval_data = evaluation_result["evaluation"]
                print(f"   Score: {eval_data.get('score', 0)}/{eval_data.get('total_questions', 0)}")
                print(f"   Percentage: {eval_data.get('percentage', 0)}%")
                print(f"   Recommendations: {len(eval_data.get('recommendations', []))}")
                print(f"   Strengths: {len(eval_data.get('strengths', []))}")
                print(f"   Weaknesses: {len(eval_data.get('weaknesses', []))}")
                
                # Check evaluation report quality
                report = eval_data.get('evaluation_report', '')
                if len(report) > 100:
                    print(f"✅ Comprehensive evaluation report ({len(report)} chars)")
                else:
                    print(f"❌ Evaluation report too brief: {report[:100]}...")
            
            # Check email sending
            if "email_sent" in evaluation_result:
                if evaluation_result["email_sent"]:
                    print("✅ Email report sent successfully")
                else:
                    print("⚠️ Email not sent (expected in test environment)")
            
            print(f"   Message: {evaluation_result.get('message', 'No message')}")

if __name__ == "__main__":
    asyncio.run(test_quiz_evaluation())