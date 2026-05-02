import json
import re
from typing import Dict, List, Optional

import httpx

from app.config import get_settings

settings = get_settings()

class LLMEngine:
    """NVIDIA NIM LLM client for medical text simplification."""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=settings.LLM_TIMEOUT)
        self.base_url = settings.NVIDIA_BASE_URL
        self.api_key = settings.NVIDIA_API_KEY
    
    async def generate(self, prompt: str, temperature: Optional[float] = None, 
                       max_tokens: Optional[int] = None) -> Dict:
        """Generate simplified medical explanation using NVIDIA LLM."""
        if temperature is None:
            temperature = settings.LLM_TEMPERATURE
        if max_tokens is None:
            max_tokens = settings.LLM_MAX_TOKENS
        
        if not self.api_key:
            # Fallback: return structured mock response
            return self._mock_generate(prompt)
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": settings.NVIDIA_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": self._get_system_prompt(),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            "temperature": temperature,
            "top_p": 0.7,
            "max_tokens": max_tokens,
            "stream": False,
        }
        
        # Try primary model
        try:
            response = await self.client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            result = response.json()
            return self._parse_response(result)
        except (httpx.HTTPError, json.JSONDecodeError) as e:
            # Try fallback model
            payload["model"] = settings.NVIDIA_FALLBACK_MODEL
            try:
                response = await self.client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                result = response.json()
                return self._parse_response(result)
            except Exception:
                return {
                    "text": f"LLM service temporarily unavailable. Error: {str(e)}",
                    "model": "error",
                    "usage": {},
                    "error": str(e),
                }
    
    def _get_system_prompt(self) -> str:
        return (
            "You are a medical report explainer. Your job is to explain medical test results "
            "in simple, clear language that an 8th-grade student can understand. "
            "\n\nRules:\n"
            "1. NEVER make definitive diagnoses. Only explain what tests measure and what results may suggest.\n"
            "2. ALWAYS recommend consulting a healthcare provider for interpretation.\n"
            "3. Use simple words and short sentences (under 20 words per sentence).\n"
            "4. Compare patient values to normal ranges clearly.\n"
            "5. Use calm, supportive tone. Do not alarm the patient unnecessarily.\n"
            "6. Format output with clear sections and bullet points.\n"
            "7. Highlight abnormal values but explain they need medical confirmation.\n"
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
            range_str = f"Normal Range: {min_v} - {max_v} {unit}"
        
        prompt = f"""Explain this medical test result to a patient in simple language.

Test: {test_name}
Patient Value: {value} {unit}
{range_str}
Status: {status}

Medical Knowledge:
{retrieved_context}

Instructions:
- Explain what {test_name} measures in 1-2 simple sentences.
- State the patient's value and normal range.
- Explain what a {status} value might mean (DO NOT diagnose).
- Keep sentences short and simple.
- Suggest 2 questions to ask the doctor.
"""
        return prompt
    
    @staticmethod
    def build_summary_prompt(tests: List[Dict], abnormal_tests: List[Dict]) -> str:
        """Build prompt for overall report summary."""
        test_list = "\n".join([
            f"- {t['test_name']}: {t['value']} {t['unit']} ({t.get('status', 'UNKNOWN')})"
            for t in tests[:10]
        ])
        
        abnormal_list = "\n".join([
            f"- {t['test_name']}: {t['value']} {t['unit']} ({t['status']})"
            for t in abnormal_tests[:5]
        ])
        
        prompt = f"""Provide a brief, reassuring summary of these medical test results for a patient.

All Tests:
{test_list}

Abnormal Results:
{abnormal_list if abnormal_list else "None"}

Instructions:
- Start with a calming statement that many results may be normal.
- Mention the abnormal results without causing alarm.
- Emphasize that only a doctor can provide proper interpretation.
- Keep to 3-4 short sentences.
- Add: "Please discuss all results with your healthcare provider."
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
