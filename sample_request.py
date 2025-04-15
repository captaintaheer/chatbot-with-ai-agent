import requests
import json

# Example using Python requests
def make_chat_request():
    url = "http://localhost:8000/chat"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    # Sample request payload with thread_id for session management
    data = {
        "message": "What is artificial intelligence?",
        "language": "English",
        "thread_id": "session_123456",  # Unique identifier for the conversation thread
        "metadata": {                    # Optional metadata for the request
            "user_id": "user_789",
            "client_version": "1.0.0"
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()  # Raise an exception for bad status codes
        
        # Parse and print the response
        result = response.json()
        print("Response:")
        print(f"Content: {result['response']}")
        print(f"Language: {result['language']}")
        
    except requests.exceptions.RequestException as e:
        print(f"Error making request: {e}")

# Example using curl (commented out as a reference)
'''
Curl command example:
curl -X POST http://localhost:8000/chat \
    -H "Content-Type: application/json" \
    -d '{"message": "What is artificial intelligence?", "language": "English"}'
'''

if __name__ == "__main__":
    make_chat_request()