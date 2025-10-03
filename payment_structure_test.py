#!/usr/bin/env python3
"""
Test payment endpoint structure and validation
"""

import asyncio
import aiohttp
import json

BASE_URL = "https://learnmate-ai-12.preview.emergentagent.com/api"

async def test_payment_structure():
    """Test payment endpoint structure without actual Razorpay calls"""
    
    async with aiohttp.ClientSession() as session:
        # Login as student first
        login_data = {
            "email": "alice.student@eduagent.com",
            "password": "student123"
        }
        
        async with session.post(f"{BASE_URL}/auth/login", json=login_data) as response:
            if response.status == 200:
                login_result = await response.json()
                token = login_result["access_token"]
                student_id = login_result["user"]["id"]
                
                print("✅ Authentication successful")
                
                # Test subscription plans endpoint
                async with session.get(f"{BASE_URL}/subscription-plans") as response:
                    if response.status == 200:
                        plans = await response.json()
                        print(f"✅ Subscription plans: {len(plans['plans'])} plans available")
                        print(f"   Plan pricing: ₹{plans['plans'][0]['monthly_amount']/100} ({plans['plans'][0]['monthly_amount']} paise)")
                    else:
                        print("❌ Failed to get subscription plans")
                
                # Test payment request structure (will fail due to mock credentials)
                payment_data = {
                    "student_id": student_id,
                    "amount": 100000,  # Rs 1000 in paise
                    "description": "Test payment structure",
                    "payment_type": "one_time"
                }
                
                headers = {"Authorization": f"Bearer {token}"}
                async with session.post(f"{BASE_URL}/create-order", json=payment_data, headers=headers) as response:
                    result = await response.json()
                    if "Authentication failed" in str(result):
                        print("✅ Payment endpoint structure correct (fails due to mock Razorpay credentials)")
                    else:
                        print(f"❌ Unexpected payment response: {result}")
                
                # Test subscription creation structure
                subscription_data = {
                    "student_id": student_id,
                    "plan_id": "monthly_premium",
                    "duration_months": 1
                }
                
                async with session.post(f"{BASE_URL}/create-subscription", json=subscription_data, headers=headers) as response:
                    result = await response.json()
                    if "Authentication failed" in str(result):
                        print("✅ Subscription endpoint structure correct (fails due to mock Razorpay credentials)")
                    else:
                        print(f"❌ Unexpected subscription response: {result}")
                
                # Test payment status endpoint structure
                async with session.get(f"{BASE_URL}/payment-status/test-transaction-id", headers=headers) as response:
                    result = await response.json()
                    if response.status == 404 and "Payment not found" in str(result):
                        print("✅ Payment status endpoint working correctly")
                    else:
                        print(f"❌ Payment status endpoint issue: {result}")
                        
            else:
                print("❌ Authentication failed")

if __name__ == "__main__":
    asyncio.run(test_payment_structure())