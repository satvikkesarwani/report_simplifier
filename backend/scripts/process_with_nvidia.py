import os
import json
import sys
import asyncio
from typing import Dict, Any

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.core.ocr_engine import OCREngine
from app.core.llm_engine import LLMEngine
from app.config import get_settings

settings = get_settings()

class LLMNativeProcessor:
    """Uses LLM logic to do both extraction and simplification in one step."""
    
    def __init__(self):
        self.ocr = OCREngine()
        self.llm = LLMEngine()

    async def process_file(self, file_path: str) -> Dict[str, Any]:
        # 1. OCR Step
        print(f"[*] Extracting text from {file_path}...")
        ocr_result = self.ocr.process_file(file_path)
        raw_text = ocr_result["text"]
        
        # 2. LLM Native Extraction & Simplification
        print("[*] Sending to NVIDIA NIM for processing...")
        prompt = self._build_native_prompt(raw_text)
        
        response = await self.llm.generate(
            prompt, 
            max_tokens=4096,
            model="meta/llama-3.1-405b-instruct" if settings.NVIDIA_API_KEY else None
        )
        
        text_output = response.get("text", "")
        
        # Attempt to parse JSON from LLM output
        try:
            # Look for JSON block
            json_match = text_output.split("```json")[-1].split("```")[0].strip()
            data = json.loads(json_match)
        except Exception:
            # Fallback parsing
            data = {"error": "Failed to parse structured JSON from LLM", "raw": text_output}
            
        return data

    def _build_native_prompt(self, text: str) -> str:
        return f"""Analyze this medical report and return a structured JSON response for a patient dashboard.

REPORT TEXT:
---
{text}
---

INSTRUCTIONS:
1. Identify all lab tests, their values, units, and reference ranges.
2. Determine the status (NORMAL, HIGH, LOW) using the reference ranges strictly.
3. For each test, provide a 1-sentence explanation of what it measures and a 1-sentence explanation of what the result means.
4. Provide an overall summary of the report in 3-4 sentences.
5. List 3 follow-up questions for the doctor.

OUTPUT FORMAT (JSON ONLY):
```json
{{
  "summary": "Overall report summary...",
  "tests": [
    {{
      "test_name": "...",
      "value": "...",
      "unit": "...",
      "normal_range": {{"min": 0, "max": 0}},
      "status": "NORMAL/HIGH/LOW",
      "explanation": "Simple explanation of test and result."
    }}
  ],
  "abnormal_count": 0,
  "follow_up_questions": ["...", "...", "..."]
}}
```
"""

async def main():
    if len(sys.argv) < 2:
        print("Usage: python3 process_with_nvidia.py <path_to_file>")
        return

    processor = LLMNativeProcessor()
    result = await processor.process_file(sys.argv[1])
    
    print("\n[!] PROCESSED DATA:")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
