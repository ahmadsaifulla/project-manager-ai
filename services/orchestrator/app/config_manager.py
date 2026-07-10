import os
import json

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
CONFIG_PATH = os.path.join(_ROOT, "workspaces", "config.json")

def get_config():
    if not os.path.exists(CONFIG_PATH):
        # Ensure workspaces dir exists
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        return {
            "repo_name": "facebook/react",
            "developer_node_url": "http://127.0.0.1:8002",
            "chatbot_node_url": "http://127.0.0.1:8001"
        }
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)

def save_config(new_config):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(new_config, f)
