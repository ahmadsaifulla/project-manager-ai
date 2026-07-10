import re

with open("test_e2e.py", "r") as f:
    content = f.read()

poll_logic = """
    print("Waiting for background task to complete...")
    for _ in range(30):
        r = requests.get(f"{BASE_URL}/api/projects/{project_id}/messages")
        st = r.json().get("pipeline_status")
        if st == "idle":
            break
        elif st == "failed":
            print(f"Pipeline failed: {r.json().get('pipeline_error')}")
            sys.exit(1)
        time.sleep(1)
    
    print("Triggering approve-goals...")
"""

content = content.replace('    print("Triggering approve-goals...")', poll_logic)

with open("test_e2e.py", "w") as f:
    f.write(content)
