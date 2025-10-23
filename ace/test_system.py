"""
Test script to verify the complete chatbot system with feedback
"""

import requests
import json
import time


def test_complete_flow():
    """Test the complete chatbot flow with feedback."""
    
    base_url = "http://localhost:8000"
    
    print("🧪 Testing Complete Chatbot Flow")
    print("=" * 50)
    
    # Step 1: Ask a question
    print("\n1. Asking a question...")
    chat_request = {
        "message": "What is machine learning?",
        "user_id": "test_user_1",
        "user_name": "Test User"
    }
    
    try:
        response = requests.post(
            f"{base_url}/chat",
            json=chat_request,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            chat_data = response.json()
            print(f"✅ Chat Response: {chat_data['response'][:100]}...")
            print(f"📝 Feedback ID: {chat_data['feedback_id']}")
            print(f"🎯 Confidence: {chat_data['confidence']}")
            
            feedback_id = chat_data['feedback_id']
            
            # Step 2: Get the original chat data
            print(f"\n2. Retrieving chat data for feedback ID: {feedback_id}")
            chat_data_response = requests.get(f"{base_url}/chat/{feedback_id}")
            
            if chat_data_response.status_code == 200:
                original_chat = chat_data_response.json()
                print(f"✅ Original Question: {original_chat['question']}")
                print(f"✅ User ID: {original_chat['user_id']}")
                print(f"✅ Model Response: {original_chat['model_response'][:100]}...")
                
                # Step 3: Submit feedback
                print(f"\n3. Submitting feedback...")
                feedback_request = {
                    "feedback_id": feedback_id,
                    "user_feedback": "The response was helpful and accurate.",
                    "feedback_type": "correct",
                    "rating": 5,
                    "additional_notes": "Great explanation!"
                }
                
                feedback_response = requests.post(
                    f"{base_url}/feedback",
                    json=feedback_request,
                    headers={"Content-Type": "application/json"}
                )
                
                if feedback_response.status_code == 200:
                    feedback_result = feedback_response.json()
                    print(f"✅ Feedback submitted: {feedback_result['message']}")
                    
                    # Step 4: Check analytics
                    print(f"\n4. Checking feedback analytics...")
                    analytics_response = requests.get(f"{base_url}/feedback/analytics")
                    
                    if analytics_response.status_code == 200:
                        analytics = analytics_response.json()
                        print(f"✅ Total feedback: {analytics.get('total_feedback', 0)}")
                        print(f"✅ Average rating: {analytics.get('average_rating', 0)}")
                        
                        # Step 5: Get user chats
                        print(f"\n5. Getting user chats...")
                        user_chats_response = requests.get(f"{base_url}/chat/user/test_user_1")
                        
                        if user_chats_response.status_code == 200:
                            user_chats = user_chats_response.json()
                            print(f"✅ User chats: {user_chats.get('total_chats', 0)}")
                            
                            print(f"\n🎉 Complete flow test successful!")
                            return True
                        else:
                            print(f"❌ Error getting user chats: {user_chats_response.status_code}")
                    else:
                        print(f"❌ Error getting analytics: {analytics_response.status_code}")
                else:
                    print(f"❌ Error submitting feedback: {feedback_response.status_code}")
            else:
                print(f"❌ Error getting chat data: {chat_data_response.status_code}")
        else:
            print(f"❌ Error in chat request: {response.status_code}")
            print(f"Error details: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection Error: Make sure the FastAPI server is running!")
        print("   Run: cd /home/suyodhan/Desktop/POC/noobPractice/ace && uv run python fastapi_chatbot.py")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        return False
    
    return False


def test_simple_question():
    """Test with a simple question to avoid recursion issues."""
    
    base_url = "http://localhost:8000"
    
    print("\n🔍 Testing Simple Question")
    print("-" * 30)
    
    # Simple question that shouldn't cause recursion
    simple_questions = [
        "Hello",
        "What time is it?",
        "Calculate 2 + 2",
        "Who am I?"
    ]
    
    for question in simple_questions:
        print(f"\nTesting: '{question}'")
        
        try:
            response = requests.post(
                f"{base_url}/chat",
                json={
                    "message": question,
                    "user_id": "test_simple",
                    "user_name": "Simple Test"
                },
                headers={"Content-Type": "application/json"},
                timeout=30  # 30 second timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Response: {data['response'][:50]}...")
                print(f"📝 Feedback ID: {data['feedback_id']}")
            else:
                print(f"❌ Error: {response.status_code} - {response.text}")
                
        except requests.exceptions.Timeout:
            print("⏰ Request timed out")
        except Exception as e:
            print(f"❌ Error: {str(e)}")


if __name__ == "__main__":
    print("🚀 Chatbot System Test Suite")
    print("=" * 50)
    
    # Test simple questions first
    test_simple_question()
    
    # Test complete flow
    print("\n" + "=" * 50)
    test_complete_flow()
    
    print("\n" + "=" * 50)
    print("Test completed!")
