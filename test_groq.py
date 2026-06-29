import os
import asyncio
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field

class TestSchema(BaseModel):
    message: str = Field(...)

async def main():
    model = ChatGroq(model="meta-llama/llama-4-scout-17b-16e-instruct", max_retries=1).with_structured_output(TestSchema)
    try:
        res = await model.ainvoke("Say hello")
        print("Success:", res)
    except Exception as e:
        print("Error:", e)

asyncio.run(main())
