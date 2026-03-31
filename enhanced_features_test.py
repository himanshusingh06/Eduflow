#!/usr/bin/env python3
"""
Test Enhanced Learning Features with Gemini Integration
"""

import asyncio
import aiohttp
import json

BASE_URL = "https://learnmate-ai-12.preview.emergentagent.com/api"

async def test_enhanced_features():
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
                student_id = login_response["user"]["id"]
                print("✅ Student login successful")
            else:
                print("❌ Student login failed")
                return
        
        # Login as parent
        parent_login = {
            "email": "carol.parent@eduagent.com",
            "password": "parent123"
        }
        
        async with session.post(f"{BASE_URL}/auth/login", json=parent_login) as response:
            if response.status == 200:
                login_response = await response.json()
                parent_token = login_response["access_token"]
                print("✅ Parent login successful")
            else:
                print("❌ Parent login failed")
                return
        
        student_headers = {"Authorization": f"Bearer {student_token}"}
        parent_headers = {"Authorization": f"Bearer {parent_token}"}
        
        # Test 1: Enhanced Learning Path Generation
        async with session.get(f"{BASE_URL}/learning-path", headers=student_headers) as response:
            if response.status == 200:
                result = await response.json()
                current_level = result.get("current_level", "unknown")
                recommended_topics = result.get("recommended_topics", [])
                weak_areas = result.get("weak_areas", [])
                strong_areas = result.get("strong_areas", [])
                print(f"✅ Enhanced Learning Path: Level {current_level}, {len(recommended_topics)} recommendations")
                print(f"   Strong areas: {len(strong_areas)}, Weak areas: {len(weak_areas)}")
            else:
                error = await response.text()
                print(f"❌ Learning path failed: {response.status} - {error}")
        
        # Test 2: Learning Insights
        async with session.get(f"{BASE_URL}/learning-insights", headers=student_headers) as response:
            if response.status == 200:
                result = await response.json()
                insights = result.get("insights", [])
                print(f"✅ Learning Insights: {len(insights)} AI-generated insights")
                
                if insights:
                    insight_types = [insight.get("insight_type", "unknown") for insight in insights]
                    print(f"   Insight types: {set(insight_types)}")
            else:
                error = await response.text()
                print(f"❌ Learning insights failed: {response.status} - {error}")
        
        # Test 3: Enhanced Parent Progress Report
        async with session.get(f"{BASE_URL}/parent/progress-report/{student_id}", headers=parent_headers) as response:
            if response.status == 200:
                result = await response.json()
                ai_insights = result.get("ai_insights", "")
                overall_perf = result.get("overall_performance", {})
                learning_path = result.get("learning_path", {})
                
                print(f"✅ Enhanced Parent Report: {len(str(ai_insights))} chars of AI insights")
                print(f"   Performance: {overall_perf.get('average_score', 0)}% avg, {overall_perf.get('total_quizzes', 0)} quizzes")
                print(f"   Learning level: {learning_path.get('current_level', 'unknown')}")
            else:
                error = await response.text()
                print(f"❌ Parent report failed: {response.status} - {error}")
        
        # Test 4: Role-based Access Control
        # Student trying to access teacher endpoint (should fail)
        async with session.get(f"{BASE_URL}/teacher/my-materials", headers=student_headers) as response:
            if response.status == 403 or "teacher" in str(await response.text()).lower():
                print("✅ Role-based access: Student correctly blocked from teacher endpoints")
            else:
                print("❌ Role-based access: Student should not access teacher endpoints")
        
        # Test 5: Error Handling - Invalid analysis ID
        async with session.get(f"{BASE_URL}/quiz/analysis/invalid-id", headers=student_headers) as response:
            if response.status == 404:
                print("✅ Error handling: Invalid analysis ID correctly rejected")
            else:
                print("❌ Error handling: Should reject invalid analysis ID")
        
        # Test 6: Authentication Required
        async with session.get(f"{BASE_URL}/learning-path") as response:
            if response.status == 401 or response.status == 403:
                print("✅ Authentication: Unauthenticated requests correctly blocked")
            else:
                print("❌ Authentication: Should require authentication")

if __name__ == "__main__":
    asyncio.run(test_enhanced_features())