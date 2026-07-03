# The Developer's Journey
*The Graveyard of Failed Alternatives*

This document serves as vital engineering history, detailing critical roadblocks and the architectural pivots required to overcome them.

## 1. OpenRouter Free Tier
* **Failed Alternative:** Attempted to run massive 70B parameter models via OpenRouter's free tier.
* **Result:** Timed out with 502 Bad Gateway errors.
* **Why:** The 60-second HTTP proxy limits enforced on free tiers cannot support the extended queuing and inference times required by 70B parameter models under heavy multi-agent load.

## 2. Llama 3.1 8B Model
* **Failed Alternative:** Downsized the LLM to a lightweight 8-billion parameter model to bypass the 60-second timeouts.
* **Result:** Crashed the backend with 500 internal server errors.
* **Why:** Small parameter models lack the reasoning depth to output pure, structured JSON consistently. The 8B model hallucinated `<function=PMOutput>` XML tags, which violently broke the strict Pydantic JSON parser.

## 3. The Reversion to Groq 70B
* **Final Selection:** Reverted the infrastructure back to the Groq API utilizing `llama-3.3-70b-versatile`.
* **Why:** This combination solves both previous failures. Groq's specialized LPU hardware delivers lightning-fast inference (bypassing all HTTP timeouts), while the massive 70B parameter model possesses the intelligence required to strictly follow complex Pydantic JSON schemas.

## 4. The QC Node Keyword Crash
* **Failed Alternative:** The QC microservice (Developer Node) crashed with a 400 Bad Request from the API when attempting to force JSON output.
* **Why:** Both Groq and OpenAI APIs strictly enforce a safety mechanism: when `response_format={"type": "json_object"}` is used, the literal word "JSON" must be physically present in the system prompt. Failing to include it prevents infinite generation loops but results in an immediate API rejection. Appending "You must output your evaluation in valid JSON format" resolved the crash.
