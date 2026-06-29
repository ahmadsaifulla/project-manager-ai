import os
import sys
from dotenv import load_dotenv

# Force the testing files to be used INSTEAD of the production ones
os.environ["ARCHITECT_FILE"] = "TEST_ARCHITECT.md"
os.environ["USER_STORIES_FILE"] = "TEST_USER_STORIES.md"

# Load the environment (which pulls in GROQ_API_KEY from backend/.env)
load_dotenv(os.path.join(os.path.dirname(__file__), "backend", ".env"))

# Add the backend directory to sys.path so we can import the graph
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "backend")))

from app.graph import app_graph
from langchain_core.messages import HumanMessage

def run_chat_session():
    # Thread ID for LangGraph memory tracking
    config = {"configurable": {"thread_id": "interactive_testing_session_1"}}
    
    print("=" * 60)
    print("🚀 DUAL-CORE AI PM TESTING PLAYGROUND")
    print("Model: llama-3.3-70b-versatile via Groq")
    print("Files targeted: TEST_ARCHITECT.md & TEST_USER_STORIES.md")
    print("Type 'exit' or 'quit' to end the session.")
    print("=" * 60)
    
    while True:
        try:
            user_input = input("\n👤 You: ")
        except (KeyboardInterrupt, EOFError):
            print("\nExiting playground...")
            break
            
        if user_input.strip().lower() in ['exit', 'quit']:
            print("Exiting playground...")
            break
            
        if not user_input.strip():
            continue
            
        print("\n⏳ [System] Running dual-core processing pass...")
        
        # Inject the human message into the graph state
        state_update = {"messages": [HumanMessage(content=user_input)]}
        
        try:
            # Invoke the graph with the current input and memory config
            result = app_graph.invoke(state_update, config=config)
            
            # Extract and print the last AI message
            messages = result.get("messages", [])
            if messages:
                last_message = messages[-1]
                print(f"🤖 PM Agent: {last_message.content}")
        except Exception as e:
            print(f"\n❌ [Error] Graph invocation failed: {e}")

if __name__ == "__main__":
    run_chat_session()
