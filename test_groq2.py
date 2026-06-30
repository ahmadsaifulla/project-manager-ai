import os
import asyncio
from typing import List
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field

class PMOutput(BaseModel):
    detected_gaps: List[str] = Field(...)
    next_question: str = Field(...)

async def main():
    try:
        model = ChatGroq(model="qwen/qwen3.6-27b", temperature=0.1)
        structured_model = model.with_structured_output(PMOutput)
        res = structured_model.invoke("Say hi and give me 2 gaps")
        print("Success:", res)
    except Exception as e:
        print("Error:", e)

asyncio.run(main())
