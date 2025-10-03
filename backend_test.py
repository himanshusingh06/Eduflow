#!/usr/bin/env python3
"""
EduAgent Backend API Testing Suite
Tests payment system, personalized learning, and parent progress reporting features
"""

import asyncio
import aiohttp
import json
import sys
from datetime import datetime
from typing import Dict, Any, Optional

# Configuration
BASE_URL = "https://learnmate-ai-12.preview.emergentagent.com/api"
TEST_USERS = {
    "student": {
        "email": "alice.student@eduagent.com",
        "password": "student123",
        "name": "Alice Johnson",
        "role": "student"
    },
    "teacher": {
        "email": "bob.teacher@eduagent.com", 
        "password": "teacher123",
        "name": "Bob Smith",
        "role": "teacher"
    },
    "parent": {
        "email": "carol.parent@eduagent.com",
        "password": "parent123", 
        "name": "Carol Wilson",
        "role": "parent"
    }
}

class EduAgentTester:
    def __init__(self):
        self.session = None
        self.tokens = {}
        self.test_results = []
        self.student_id = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def log_result(self, test_name: str, success: bool, message: str, details: Any = None):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {message}")
        
        self.test_results.append({
            "test": test_name,
            "success": success,
            "message": message,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })
        
        if details and not success:
            print(f"   Details: {details}")
    
    async def make_request(self, method: str, endpoint: str, data: Dict = None, 
                          token: str = None, params: Dict = None) -> tuple[bool, Any]:
        """Make HTTP request to API"""
        url = f"{BASE_URL}{endpoint}"
        headers = {"Content-Type": "application/json"}
        
        if token:
            headers["Authorization"] = f"Bearer {token}"
            
        try:
            async with self.session.request(
                method, url, json=data, headers=headers, params=params
            ) as response:
                response_data = await response.json()
                return response.status < 400, response_data
        except Exception as e:
            return False, {"error": str(e)}
    
    async def register_and_login_users(self):
        """Register and login test users"""
        print("\n🔐 Setting up test users...")
        
        for role, user_data in TEST_USERS.items():
            # Try to register (might fail if user exists)
            success, response = await self.make_request("POST", "/auth/register", user_data)
            
            if not success and "already registered" not in str(response):
                self.log_result(f"Register {role}", False, f"Registration failed: {response}")
                continue
            
            # Login to get token
            login_data = {"email": user_data["email"], "password": user_data["password"]}
            success, response = await self.make_request("POST", "/auth/login", login_data)
            
            if success and "access_token" in response:
                self.tokens[role] = response["access_token"]
                if role == "student":
                    self.student_id = response["user"]["id"]
                self.log_result(f"Login {role}", True, "Successfully authenticated")
            else:
                self.log_result(f"Login {role}", False, f"Login failed: {response}")
    
    async def test_payment_system(self):
        """Test Payment System APIs"""
        print("\n💳 Testing Payment System APIs...")
        
        if "student" not in self.tokens:
            self.log_result("Payment System", False, "No student token available")
            return
        
        student_token = self.tokens["student"]
        
        # Test 1: Get subscription plans
        success, response = await self.make_request("GET", "/subscription-plans")
        if success and "plans" in response:
            plans = response["plans"]
            if plans and len(plans) > 0:
                plan = plans[0]
                if plan.get("monthly_amount") == 100000:  # Rs 1000 in paise
                    self.log_result("Get Subscription Plans", True, f"Found {len(plans)} plans, Rs 1000/month plan available")
                else:
                    self.log_result("Get Subscription Plans", False, f"Expected Rs 1000 plan, got {plan.get('monthly_amount', 'unknown')} paise")
            else:
                self.log_result("Get Subscription Plans", False, "No plans returned")
        else:
            self.log_result("Get Subscription Plans", False, f"Failed to get plans: {response}")
        
        # Test 2: Create subscription
        subscription_data = {
            "student_id": self.student_id,
            "plan_id": "monthly_premium",
            "duration_months": 1
        }
        success, response = await self.make_request("POST", "/create-subscription", subscription_data, student_token)
        
        subscription_id = None
        if success and response.get("success"):
            subscription_id = response.get("subscription_id")
            self.log_result("Create Subscription", True, f"Subscription created: {subscription_id}")
        else:
            self.log_result("Create Subscription", False, f"Failed to create subscription: {response}")
        
        # Test 3: Create one-time payment
        payment_data = {
            "student_id": self.student_id,
            "amount": 100000,  # Rs 1000
            "description": "Test payment for premium access",
            "payment_type": "one_time"
        }
        success, response = await self.make_request("POST", "/create-payment", payment_data, student_token)
        
        transaction_id = None
        if success and response.get("success"):
            transaction_id = response.get("transaction_id")
            self.log_result("Create Payment", True, f"Payment created: {transaction_id}")
        else:
            self.log_result("Create Payment", False, f"Failed to create payment: {response}")
        
        # Test 4: Check payment status
        if transaction_id:
            success, response = await self.make_request("GET", f"/payment-status/{transaction_id}", token=student_token)
            if success and "status" in response:
                self.log_result("Check Payment Status", True, f"Payment status: {response['status']}")
            else:
                self.log_result("Check Payment Status", False, f"Failed to check status: {response}")
        
        # Test 5: Mock payment success
        if transaction_id:
            success, response = await self.make_request("GET", f"/mock-payment/{transaction_id}")
            if success:
                self.log_result("Mock Payment Success", True, "Payment marked as successful")
                
                # Verify status updated
                success, response = await self.make_request("GET", f"/payment-status/{transaction_id}", token=student_token)
                if success and response.get("status") == "SUCCESS":
                    self.log_result("Payment Status Update", True, "Payment status correctly updated to SUCCESS")
                else:
                    self.log_result("Payment Status Update", False, f"Status not updated: {response}")
            else:
                self.log_result("Mock Payment Success", False, f"Mock payment failed: {response}")
        
        # Test 6: Get user subscription
        success, response = await self.make_request("GET", "/my-subscription", token=student_token)
        if success:
            self.log_result("Get My Subscription", True, f"Subscription status: {response}")
        else:
            self.log_result("Get My Subscription", False, f"Failed to get subscription: {response}")
    
    async def test_personalized_learning(self):
        """Test Personalized Learning APIs"""
        print("\n🧠 Testing Personalized Learning APIs...")
        
        if "student" not in self.tokens:
            self.log_result("Personalized Learning", False, "No student token available")
            return
        
        student_token = self.tokens["student"]
        
        # Test 1: Get learning path
        success, response = await self.make_request("GET", "/learning-path", token=student_token)
        if success and "student_id" in response:
            self.log_result("Get Learning Path", True, f"Learning path generated for level: {response.get('current_level')}")
            
            # Verify AI-generated recommendations
            if response.get("recommended_topics") and len(response["recommended_topics"]) > 0:
                self.log_result("AI Learning Recommendations", True, f"Generated {len(response['recommended_topics'])} topic recommendations")
            else:
                self.log_result("AI Learning Recommendations", False, "No topic recommendations generated")
        else:
            self.log_result("Get Learning Path", False, f"Failed to get learning path: {response}")
        
        # Test 2: Update learning progress
        completed_topic = "Basic Mathematics"
        success, response = await self.make_request("POST", "/update-learning-progress", 
                                                   {"completed_topic": completed_topic}, student_token)
        if success and "message" in response:
            self.log_result("Update Learning Progress", True, f"Progress updated for topic: {completed_topic}")
        else:
            self.log_result("Update Learning Progress", False, f"Failed to update progress: {response}")
        
        # Test 3: Get learning insights
        success, response = await self.make_request("GET", "/learning-insights", token=student_token)
        if success and "insights" in response:
            insights = response["insights"]
            self.log_result("Get Learning Insights", True, f"Generated {len(insights)} AI-powered insights")
            
            # Check for different types of insights
            insight_types = [insight.get("type") for insight in insights]
            if any(t in insight_types for t in ["performance", "recommendation", "achievement"]):
                self.log_result("AI Insight Types", True, f"Generated diverse insight types: {set(insight_types)}")
            else:
                self.log_result("AI Insight Types", False, f"Limited insight types: {insight_types}")
        else:
            self.log_result("Get Learning Insights", False, f"Failed to get insights: {response}")
    
    async def test_parent_progress_reporting(self):
        """Test Parent Progress Reporting APIs"""
        print("\n👨‍👩‍👧‍👦 Testing Parent Progress Reporting APIs...")
        
        if "parent" not in self.tokens:
            self.log_result("Parent Progress", False, "No parent token available")
            return
        
        parent_token = self.tokens["parent"]
        
        # Test 1: Get linked students
        success, response = await self.make_request("GET", "/parent/students", token=parent_token)
        if success and "students" in response:
            students = response["students"]
            self.log_result("Get Linked Students", True, f"Found {len(students)} linked students")
            
            if students and len(students) > 0:
                test_student_id = students[0]["id"]
                
                # Test 2: Get progress report for student
                success, response = await self.make_request("GET", f"/parent/progress-report/{test_student_id}", token=parent_token)
                if success and "student_info" in response:
                    report = response
                    self.log_result("Get Progress Report", True, f"Generated progress report for student: {report['student_info']['name']}")
                    
                    # Verify report components
                    required_sections = ["overall_performance", "subject_performance", "recent_activities", "learning_path", "ai_insights"]
                    missing_sections = [section for section in required_sections if section not in report]
                    
                    if not missing_sections:
                        self.log_result("Progress Report Completeness", True, "All required report sections present")
                    else:
                        self.log_result("Progress Report Completeness", False, f"Missing sections: {missing_sections}")
                    
                    # Check AI insights
                    if report.get("ai_insights") and len(str(report["ai_insights"])) > 50:
                        self.log_result("AI Progress Insights", True, "AI-generated insights included in report")
                    else:
                        self.log_result("AI Progress Insights", False, "AI insights missing or too brief")
                        
                    # Check performance analytics
                    overall_perf = report.get("overall_performance", {})
                    if "average_score" in overall_perf and "total_quizzes" in overall_perf:
                        self.log_result("Performance Analytics", True, f"Analytics: {overall_perf['total_quizzes']} quizzes, {overall_perf['average_score']}% avg")
                    else:
                        self.log_result("Performance Analytics", False, "Performance analytics incomplete")
                        
                else:
                    self.log_result("Get Progress Report", False, f"Failed to get progress report: {response}")
            else:
                self.log_result("Get Progress Report", False, "No students available for testing")
        else:
            self.log_result("Get Linked Students", False, f"Failed to get students: {response}")
    
    async def test_role_based_access(self):
        """Test role-based access controls"""
        print("\n🔒 Testing Role-based Access Controls...")
        
        # Test student accessing parent endpoints
        if "student" in self.tokens and self.student_id:
            student_token = self.tokens["student"]
            
            # Should fail - student accessing parent endpoint
            success, response = await self.make_request("GET", "/parent/students", token=student_token)
            if not success or "Parent access required" in str(response):
                self.log_result("Student->Parent Access Block", True, "Student correctly blocked from parent endpoints")
            else:
                self.log_result("Student->Parent Access Block", False, "Student should not access parent endpoints")
        
        # Test accessing endpoints without authentication
        success, response = await self.make_request("GET", "/learning-path")
        if not success:
            self.log_result("Unauthenticated Access Block", True, "Unauthenticated requests correctly blocked")
        else:
            self.log_result("Unauthenticated Access Block", False, "Should require authentication")
    
    async def test_ai_integration(self):
        """Test AI integration functionality"""
        print("\n🤖 Testing AI Integration...")
        
        if "student" not in self.tokens:
            self.log_result("AI Integration", False, "No student token available")
            return
        
        student_token = self.tokens["student"]
        
        # Test AI question answering
        question_data = {
            "question": "What is photosynthesis and why is it important?",
            "subject": "Biology"
        }
        success, response = await self.make_request("POST", "/qa/ask", question_data, student_token)
        if success and "answer" in response:
            answer = response["answer"]
            if len(answer) > 50 and "photosynthesis" in answer.lower():
                self.log_result("AI Question Answering", True, f"Generated comprehensive answer ({len(answer)} chars)")
            else:
                self.log_result("AI Question Answering", False, f"Answer too brief or irrelevant: {answer[:100]}...")
        else:
            self.log_result("AI Question Answering", False, f"Failed to get AI answer: {response}")
        
        # Test AI quiz generation
        quiz_data = {
            "title": "Biology Test Quiz",
            "subject": "Biology", 
            "grade_level": "Grade 10",
            "topic": "Photosynthesis",
            "num_questions": 5,
            "difficulty": "medium"
        }
        success, response = await self.make_request("POST", "/quiz/generate", quiz_data, student_token)
        if success and "questions" in response:
            questions = response["questions"]
            if len(questions) >= 3:  # Allow some flexibility
                self.log_result("AI Quiz Generation", True, f"Generated {len(questions)} quiz questions")
                
                # Check question quality
                first_question = questions[0]
                if ("question" in first_question and "options" in first_question and 
                    len(first_question["options"]) == 4):
                    self.log_result("AI Quiz Quality", True, "Questions have proper structure")
                else:
                    self.log_result("AI Quiz Quality", False, "Questions missing required fields")
            else:
                self.log_result("AI Quiz Generation", False, f"Expected 5 questions, got {len(questions)}")
        else:
            self.log_result("AI Quiz Generation", False, f"Failed to generate quiz: {response}")
    
    async def run_all_tests(self):
        """Run all test suites"""
        print("🚀 Starting EduAgent Backend API Tests")
        print("=" * 50)
        
        try:
            await self.register_and_login_users()
            await self.test_payment_system()
            await self.test_personalized_learning()
            await self.test_parent_progress_reporting()
            await self.test_role_based_access()
            await self.test_ai_integration()
            
        except Exception as e:
            self.log_result("Test Suite", False, f"Test suite failed with error: {str(e)}")
        
        # Print summary
        print("\n" + "=" * 50)
        print("📊 TEST SUMMARY")
        print("=" * 50)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print("\n🔍 FAILED TESTS:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  • {result['test']}: {result['message']}")
        
        return passed_tests, failed_tests

async def main():
    """Main test runner"""
    async with EduAgentTester() as tester:
        passed, failed = await tester.run_all_tests()
        
        # Exit with error code if tests failed
        if failed > 0:
            sys.exit(1)
        else:
            print("\n🎉 All tests passed!")
            sys.exit(0)

if __name__ == "__main__":
    asyncio.run(main())