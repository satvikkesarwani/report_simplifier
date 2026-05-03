import json
import re
import base64
from typing import Any, Dict, List, Optional

from openai import AsyncOpenAI

from app.config import get_settings

settings = get_settings()

class LLMEngine:
    """NVIDIA NIM LLM client for medical text simplification."""
    
    def __init__(self):
        self.client = AsyncOpenAI(
            base_url=settings.NVIDIA_BASE_URL,
            api_key=settings.NVIDIA_API_KEY
        )
        self.model = settings.NVIDIA_MODEL
        self.fallback_model = settings.NVIDIA_FALLBACK_MODEL
    
    async def generate(self, prompt: str, temperature: Optional[float] = None, 
                       max_tokens: Optional[int] = None,
                       model: Optional[str] = None,
                       fallback_model: Optional[str] = None) -> Dict:
        """Generate simplified medical explanation using NVIDIA LLM."""
        if temperature is None:
            temperature = settings.LLM_TEMPERATURE
        if max_tokens is None:
            max_tokens = settings.LLM_MAX_TOKENS
        
        target_model = model or self.model
        
        if not settings.NVIDIA_API_KEY:
            # Fallback: return structured mock response
            return self._mock_generate(prompt)
        
        try:
            response = await self.client.chat.completions.create(
                model=target_model,
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=0.7,
            )
            
            return {
                "text": response.choices[0].message.content,
                "model": response.model,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
            }
        except Exception as e:
            # Try fallback model
            try:
                response = await self.client.chat.completions.create(
                    model=fallback_model or self.fallback_model,
                    messages=[
                        {"role": "system", "content": self._get_system_prompt()},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=temperature,
                    max_tokens=max_tokens,
                    top_p=0.7,
                )
                return {
                    "text": response.choices[0].message.content,
                    "model": response.model,
                    "usage": {
                        "prompt_tokens": response.usage.prompt_tokens,
                        "completion_tokens": response.usage.completion_tokens,
                        "total_tokens": response.usage.total_tokens
                    }
                }
            except Exception as final_exc:
                return {
                    "text": f"LLM service temporarily unavailable. Error: {str(final_exc)}",
                    "model": "error",
                    "usage": {}
                }

    async def generate_native_report(self, text: str) -> Dict[str, Any]:
        """Use LLM to perform end-to-end extraction and simplification."""
        prompt = f"""Analyze this medical report and return a structured JSON response for a patient dashboard.

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
  "document_type": "...",
  "tests": [
    {{
      "test_name": "...",
      "value": "...",
      "unit": "...",
      "normal_range": {{"min": 0, "max": 0, "text": "..."}},
      "status": "NORMAL/HIGH/LOW",
      "explanation": "Simple explanation of test and result."
    }}
  ],
  "abnormal_count": 0,
  "follow_up_questions": ["...", "...", "..."]
}}
```
"""
        response = await self.generate(prompt, max_tokens=4096)
        text_output = response.get("text", "")
        
        try:
            # Look for JSON block
            if "```json" in text_output:
                json_match = text_output.split("```json")[-1].split("```")[0].strip()
            else:
                json_match = text_output.strip()
            return json.loads(json_match)
        except Exception:
            return {
                "summary": "Failed to parse AI output. Raw response below.",
                "tests": [],
                "error": text_output
            }

    async def aclose(self) -> None:
        """Close the underlying OpenAI client."""
        await self.client.close()

    async def generate_ocr_from_vision(self, image_path: str) -> str:
        """Use NVIDIA Vision model to extract text from a report image."""
        try:
            with open(image_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode("utf-8")

            # Determine file extension/mime
            ext = image_path.split(".")[-1].lower()
            mime_type = f"image/{ext}" if ext in ["png", "jpg", "jpeg"] else "image/png"

            response = await self.client.chat.completions.create(
                model=settings.NVIDIA_VISION_MODEL,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Extract all text from this medical report image exactly as it appears. Maintain the tabular structure if possible."},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:{mime_type};base64,{base64_image}"},
                            },
                        ],
                    }
                ],
                max_tokens=4096,
                temperature=0.2,
            )

            return response.choices[0].message.content
        except Exception as e:
            # Fallback to local OCR if vision fails
            print(f"[!] NVIDIA Vision OCR failed: {e}. Falling back to local OCR...")
            from app.core.ocr_engine import OCREngine
            ocr = OCREngine()
            result = ocr.process_file(image_path)
            return result["text"]
    def _get_system_prompt(self) -> str:
        return (
            "You are a medical report explainer. Your job is to explain medical test results "
            "in simple, clear language that an 8th-grade student can understand. "
            "\n\nCRITICAL RULES:\n"
            "1. STRICT GROUNDING: You MUST respect the 'Status' label (NORMAL, HIGH, LOW, UNKNOWN) provided in the data. "
            "Never override it based on your internal knowledge. If a value is NORMAL, explain it as reassuring. "
            "If a value is UNKNOWN, state that it could not be confidently interpreted.\n"
            "2. NEVER make definitive diagnoses. Only explain what tests measure and what results may suggest.\n"
            "3. ALWAYS recommend consulting a healthcare provider for interpretation.\n"
            "4. Use simple words and short sentences (under 20 words per sentence).\n"
            "5. Compare patient values to normal ranges clearly.\n"
            "6. Use calm, supportive tone. Do not alarm the patient unnecessarily.\n"
            "7. Format output with clear sections and bullet points.\n"
            "8. Suggest 2-3 questions the patient can ask their doctor."
        )
    
    def _parse_response(self, result: Dict) -> Dict:
        """Parse NVIDIA API response."""
        choices = result.get("choices", [])
        if not choices:
            return {"text": "No response generated.", "model": "unknown", "usage": {}}
        
        message = choices[0].get("message", {})
        text = message.get("content", "")
        
        return {
            "text": text,
            "model": result.get("model", "unknown"),
            "usage": result.get("usage", {}),
        }
    
    def _mock_generate(self, prompt: str) -> Dict:
        """Generate mock response when API key is not available."""
        if "Explain this medical report" in prompt:
            report_type_match = re.search(r"Report Type:\s*([^\n]+)", prompt)
            report_type = report_type_match.group(1).strip().replace("_", " ") if report_type_match else "medical report"

            entity_match = re.search(r"Detected Terms:\s*([^\n]+)", prompt)
            terms = entity_match.group(1).strip() if entity_match else "the key findings"

            response = (
                f"This {report_type} contains information about {terms}. "
                "I have rewritten it in simpler language so you can understand the main findings, "
                "but a doctor should still confirm what it means for your care.\n\n"
                "Important points:\n"
                "- Review the main findings with your doctor.\n"
                "- Ask whether any follow-up tests, medicines, or precautions are needed.\n"
                "- Use this explanation as educational support, not as a diagnosis."
            )

            return {
                "text": response,
                "model": "mock_fallback",
                "usage": {
                    "prompt_tokens": len(prompt.split()),
                    "completion_tokens": len(response.split()),
                },
            }

        # Extract test info from prompt for a basic response
        test_match = re.search(r"Test:\s*([^\n]+)", prompt)
        test_name = test_match.group(1).strip() if test_match else "Unknown Test"
        
        value_match = re.search(r"Patient Value:\s*([^\n]+)", prompt)
        patient_value = value_match.group(1).strip() if value_match else "N/A"
        
        status_match = re.search(r"Status:\s*([^\n]+)", prompt)
        status = status_match.group(1).strip() if status_match else "UNKNOWN"
        
        # Find context in prompt
        context_match = re.search(r"Medical Knowledge:\s*([\s\S]+?)(?=\n\nPatient|$)", prompt)
        context = context_match.group(1).strip() if context_match else ""
        
        response = f"""## {test_name}

**Your Result:** {patient_value} ({status})

**What this test measures:**
{self._extract_what_measures(context, test_name)}

**What your result means:**
{self._generate_status_explanation(test_name, patient_value, status, context)}

**Important:** These explanations are for educational purposes only. Please discuss your results with your doctor for proper medical advice.

**Questions to ask your doctor:**
1. What could be causing my {test_name} to be {status.lower()}?
2. Should I repeat this test or do additional testing?
3. Are there any lifestyle changes that might help?
"""
        
        return {
            "text": response,
            "model": "mock_fallback",
            "usage": {"prompt_tokens": len(prompt.split()), "completion_tokens": len(response.split())},
        }
    
    def _extract_what_measures(self, context: str, test_name: str) -> str:
        """Extract what a test measures from context."""
        sentences = context.split(".")
        for s in sentences[:3]:
            s = s.strip()
            if s and ("measures" in s.lower() or "test" in s.lower() or "blood" in s.lower()):
                return s + "."
        return f"The {test_name} measures a component in your blood that helps doctors assess your health."
    
    def _generate_status_explanation(self, test_name: str, value: str, status: str, context: str) -> str:
        """Generate basic status explanation."""
        if value == "N/A" or status == "UNKNOWN":
            return f"We could not confidently extract or interpret the result for {test_name}. A manual review of the original report is recommended."
        
        if status == "NORMAL":
            return f"Your {test_name} result of {value} is within the normal range. This is generally a good sign."
        elif "LOW" in status:
            return f"Your {test_name} result of {value} is below the normal range. This may suggest a deficiency or other condition, but only your doctor can determine the exact cause."
        elif "HIGH" in status:
            return f"Your {test_name} result of {value} is above the normal range. This may indicate stress, infection, or other factors. Your doctor will help identify the cause."
        else:
            return f"Your {test_name} result is {value}. Please consult your doctor for proper interpretation."


class PromptBuilder:
    """Builds structured prompts for LLM medical simplification."""
    
    @staticmethod
    def build_test_prompt(test: Dict, retrieved_context: str) -> str:
        """Build prompt for a single test explanation."""
        test_name = test.get("test_name", "Unknown")
        value = test.get("value", "N/A")
        unit = test.get("unit", "")
        status = test.get("status", "UNKNOWN")
        range_info = test.get("normal_range", {})
        
        range_str = ""
        if range_info:
            min_v = range_info.get("min", "?")
            max_v = range_info.get("max", "?")
            range_str = f"Reference Range: {min_v} - {max_v} {unit}"
        
        context = retrieved_context[:700] if retrieved_context else "No extra context."

        prompt = f"""Explain this medical test result in simple language.
IMPORTANT: The 'Status' has been determined by a deterministic rule engine. You MUST follow it.

Test: {test_name}
Value: {value} {unit}
{range_str}
Status: {status}
Medical Knowledge: {context}

Instructions:
1. If Status is UNKNOWN, explain that the value could not be confidently interpreted and needs manual check.
2. If Status is NORMAL, reassure the patient.
3. If Status is HIGH or LOW, explain what the test measures and what deviation might mean, without diagnosing.
4. Write exactly 4 short bullet points:
   - what the test measures
   - what this result means (respect the Status label!)
   - one safety note (not a diagnosis)
   - one question to ask a doctor
"""
        return prompt
    
    @staticmethod
    def build_summary_prompt(tests: List[Dict], abnormal_tests: List[Dict]) -> str:
        """Build prompt for overall report summary."""
        test_list = "\n".join([
            f"- {t['test_name']}: {t['value']} {t['unit']} ({t.get('status', 'UNKNOWN')})"
            for t in tests[:10]
        ])

        normal_list = "\n".join([
            f"- {t['test_name']}: {t['value']} {t['unit']} ({t['status']})"
            for t in tests
            if str(t.get("status", "")).upper() == "NORMAL"
        ][:5])
        
        abnormal_list = "\n".join([
            f"- {t['test_name']}: {t['value']} {t['unit']} ({t['status']})"
            for t in abnormal_tests[:5]
        ])
        
        prompt = f"""Explain these medical test results for a patient in a balanced way.

All Tests:
{test_list}

Reassuring / Normal Results:
{normal_list if normal_list else "None clearly identified"}

Abnormal Results:
{abnormal_list if abnormal_list else "None"}

Instructions:
- Write in plain English with short sentences.
- Include both positives and negatives.
- Use these exact section headings:
  Overview:
  Good signs:
  Needs attention:
  What to ask your doctor:
- Mention reassuring findings when present.
- Mention concerning findings calmly, without diagnosing.
- End by reminding the patient that only a doctor can interpret the full report in context.
"""
        return prompt

    @staticmethod
    def build_report_prompt(raw_text: str, document_type: str, entity_names: List[str]) -> str:
        detected_terms = ", ".join(entity_names[:12]) if entity_names else "No key entities detected"
        excerpt = raw_text[:5000]

        return f"""Explain this medical report in simple patient-friendly language.

Report Type: {document_type}
Detected Terms: {detected_terms}

Original Report Excerpt:
{excerpt}

Instructions:
- Summarize the main findings in plain English.
- Avoid making a diagnosis or treatment decision.
- Explain any difficult medical terms in context.
- Mention what the patient should discuss with a doctor next.
- Keep the tone calm, supportive, and easy to understand.
"""
    
    @staticmethod
    def build_glossary_prompt(term: str) -> str:
        """Build prompt for a single medical term definition."""
        return f"""Explain the medical term '{term}' in very simple language that a 10-year-old could understand.

Rules:
- Use only common words.
- 1-2 sentences maximum.
- Give a simple example if helpful.
"""
