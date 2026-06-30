import sys
import os

# Add the app dir to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.graph import get_llm_model, invoke_llm
from app.schemas import PMOutput

def test():
    model = get_llm_model()
    structured = model.with_structured_output(PMOutput)
    
    prompt = """
You are a PM. The user just said: "I want to build a digital marketing system. It should have AI features."
History:
User: Hello
Assistant: Welcome! What project are we planning today?
User: I want to build a digital marketing system. It should have AI features.

Phase is 'listening'. Acknowledge the input and ask for more details.
"""
    print("Invoking LLM...")
    try:
        res = invoke_llm(structured, prompt)
        print("Result:", res)
    except Exception as e:
        print("Exception:", e)

if __name__ == "__main__":
    test()
