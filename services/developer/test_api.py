import requests
import json
import sys

URL = "http://127.0.0.1:8000/api/qc/evaluate"

# Using a popular public repo for testing. 
# Make sure the repo actually has a 'main' branch and the branch you specify exists.
payload = {
    "task_id": "TEST-QC-001",
    "repo_name": "facebook/react", # Public repo with 'main' branch
    "branch_name": "main"          # Comparing main to main to ensure auth and graph execute correctly
}

print(f"Sending POST request to {URL}...")
print(f"Payload: {json.dumps(payload, indent=2)}\n")

try:
    response = requests.post(URL, json=payload)
    
    # Check if the server returned an error
    if response.status_code != 200:
        print(f"❌ HTTP Error {response.status_code}: {response.text}")
        sys.exit(1)
        
    data = response.json()
    
    print("✅ --- RESPONSE FROM QC ENGINE ---")
    print(f"Verdict: {'APPROVED' if data.get('verdict') else 'REJECTED'}")
    print("\nFeedback:")
    print(data.get("feedback", "No feedback provided."))
    print("---------------------------------")
    
except requests.exceptions.ConnectionError:
    print("❌ Connection Error: Ensure your FastAPI server is running on port 8000.")
except Exception as e:
    print(f"❌ Unexpected Error: {str(e)}")
