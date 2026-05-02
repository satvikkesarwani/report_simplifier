import asyncio
import re
from typing import Any, Dict, List, Optional

from app.utils.readability import analyze_readability


class PipelineService:
    """Orchestrates the full OCR -> NLP -> RAG -> LLM pipeline."""

    def __init__(self):
        self._ocr = None
        self._nlp = None
        self._rag = None
        self._llm = None
        self._prompt_builder = None

    @property
    def ocr(self):
        if self._ocr is None:
            from app.core.ocr_engine import OCREngine

            self._ocr = OCREngine()
        return self._ocr

    @property
    def nlp(self):
        if self._nlp is None:
            from app.core.nlp_engine import NLPEngine

            self._nlp = NLPEngine()
        return self._nlp

    @property
    def rag(self):
        if self._rag is None:
            from app.core.rag_engine import RAGEngine

            self._rag = RAGEngine()
        return self._rag

    @property
    def llm(self):
        if self._llm is None:
            from app.core.llm_engine import LLMEngine

            self._llm = LLMEngine()
        return self._llm

    @property
    def prompt_builder(self):
        if self._prompt_builder is None:
            from app.core.llm_engine import PromptBuilder

            self._prompt_builder = PromptBuilder()
        return self._prompt_builder

    async def process_report(self, file_path: str) -> Dict[str, Any]:
        """Run complete processing pipeline on a medical report file."""
        result: Dict[str, Any] = {
            "file_path": file_path,
            "status": "processing",
            "stages": {},
            "errors": [],
        }

        try:
            ocr_result = self.ocr.process_file(file_path)
            result["stages"]["ocr"] = {
                "status": "completed",
                "pages": ocr_result.get("pages", 0),
                "method": ocr_result.get("method", "unknown"),
            }
            raw_text = ocr_result["text"]
            result["raw_text"] = raw_text
            result["ocr_layout_pages"] = ocr_result.get("layout_pages", [])
        except Exception as exc:
            result["stages"]["ocr"] = {"status": "failed", "error": str(exc)}
            result["errors"].append(f"OCR failed: {exc}")
            result["status"] = "failed"
            return result

        try:
            nlp_result = self.nlp.process_text(raw_text)
            structured_tests = nlp_result["structured_tests"]
            document_type = self._detect_document_type(raw_text, structured_tests)
            result["document_type"] = document_type
            result["stages"]["nlp"] = {
                "status": "completed",
                "entities_found": len(nlp_result.get("entities", [])),
                "tests_found": len(structured_tests),
                "document_type": document_type,
            }
            result["structured_data"] = nlp_result
        except Exception as exc:
            result["stages"]["nlp"] = {"status": "failed", "error": str(exc)}
            result["errors"].append(f"NLP failed: {exc}")
            result["status"] = "failed"
            return result

        if structured_tests:
            simplified_output = await self._process_structured_tests(structured_tests)
        else:
            simplified_output = await self._process_narrative_report(
                raw_text=raw_text,
                nlp_result=result["structured_data"],
                document_type=result["document_type"],
            )

        result["stages"]["simplification"] = {
            "status": "completed",
            "tests_processed": len(simplified_output.get("tests", [])),
            "abnormal_tests": simplified_output.get("abnormal_count", 0),
            "mode": "structured_tests" if structured_tests else "narrative_report",
        }

        simplified_text = self._flatten_simplified_text(simplified_output)
        readability = analyze_readability(simplified_text)
        result["evaluation"] = {
            "readability": readability,
            "extraction": {
                "entities_found": len(result["structured_data"].get("entities", [])),
                "tests_found": len(result["structured_data"].get("structured_tests", [])),
                "abnormal_tests": simplified_output.get("abnormal_count", 0),
            },
        }

        result["structured_data"]["visual_overlays"] = self._build_visual_overlays(
            layout_pages=result.get("ocr_layout_pages", []),
            entities=result["structured_data"].get("entities", []),
            abnormal_tests=simplified_output.get("abnormal_tests", []),
        )
        result.pop("ocr_layout_pages", None)

        result["simplified_output"] = simplified_output
        result["status"] = "completed"
        return result

    def process_report_sync(self, file_path: str) -> Dict[str, Any]:
        """Synchronous wrapper for process_report."""
        return asyncio.run(self.process_report(file_path))

    async def _process_structured_tests(self, structured_tests: List[Dict[str, Any]]) -> Dict[str, Any]:
        simplified_tests: List[Dict[str, Any]] = []
        abnormal_tests: List[Dict[str, Any]] = []

        for test in structured_tests:
            try:
                retrieved = self.rag.retrieve_for_test(
                    test["test_name"],
                    test.get("value", ""),
                    test.get("status", ""),
                )
                context = self.rag.format_context(retrieved)
                prompt = self.prompt_builder.build_test_prompt(test, context)
                llm_response = await self.llm.generate(prompt)
                explanation = llm_response.get("text", "")

                simplified_test = {
                    **test,
                    "explanation": explanation,
                    "retrieved_sources": [item.get("title", "") for item in retrieved],
                    "llm_model": llm_response.get("model", "unknown"),
                }
                simplified_tests.append(simplified_test)

                if test.get("status") not in ["NORMAL", "UNKNOWN"]:
                    abnormal_tests.append(simplified_test)
            except Exception as exc:
                simplified_test = {
                    **test,
                    "explanation": (
                        f"Could not generate a detailed explanation for {test['test_name']}. "
                        "Please discuss this result with your doctor."
                    ),
                    "retrieved_sources": [],
                    "llm_model": "error",
                    "error": str(exc),
                }
                simplified_tests.append(simplified_test)

        try:
            summary_prompt = self.prompt_builder.build_summary_prompt(
                simplified_tests,
                abnormal_tests,
            )
            summary_response = await self.llm.generate(summary_prompt, max_tokens=512)
            summary = summary_response.get("text", "")
        except Exception:
            summary = (
                "Your medical report has been processed. Please review the simplified "
                "explanations and discuss them with your doctor."
            )

        glossary = await self._build_glossary(simplified_tests, fallback_terms=[])

        return {
            "summary": summary,
            "tests": simplified_tests,
            "abnormal_tests": abnormal_tests,
            "abnormal_count": len(abnormal_tests),
            "total_tests": len(simplified_tests),
            "glossary": glossary,
            "report_explanation": "",
            "follow_up_questions": self._build_follow_up_questions(
                document_type="lab_report",
                abnormal_tests=abnormal_tests,
            ),
        }

    async def _process_narrative_report(
        self,
        *,
        raw_text: str,
        nlp_result: Dict[str, Any],
        document_type: str,
    ) -> Dict[str, Any]:
        report_prompt = self.prompt_builder.build_report_prompt(
            raw_text=raw_text,
            document_type=document_type,
            entity_names=self._extract_entity_names(nlp_result),
        )

        try:
            report_response = await self.llm.generate(report_prompt, max_tokens=900)
            report_explanation = report_response.get("text", "")
        except Exception:
            report_explanation = (
                "This report appears to be more narrative than tabular. Please review the "
                "key findings with your doctor to understand the clinical context."
            )

        glossary_terms = self._select_glossary_terms(nlp_result)
        glossary = await self._build_glossary([], fallback_terms=glossary_terms)

        summary = self._build_narrative_summary(report_explanation)

        return {
            "summary": summary,
            "tests": [],
            "abnormal_tests": [],
            "abnormal_count": 0,
            "total_tests": 0,
            "glossary": glossary,
            "report_explanation": report_explanation,
            "follow_up_questions": self._build_follow_up_questions(
                document_type=document_type,
                abnormal_tests=[],
            ),
        }

    async def _build_glossary(
        self,
        tests: List[Dict[str, Any]],
        *,
        fallback_terms: List[str],
    ) -> Dict[str, str]:
        glossary: Dict[str, str] = {}
        terms = [test["test_name"] for test in tests if test["test_name"] != "Unknown Test"]
        terms.extend(term for term in fallback_terms if term not in terms)

        for term in terms[:10]:
            try:
                prompt = self.prompt_builder.build_glossary_prompt(term)
                glossary_response = await self.llm.generate(prompt, max_tokens=100)
                glossary[term] = glossary_response.get("text", "").strip()
            except Exception:
                glossary[term] = f"{term} is a medical term used in your report."

        return glossary

    def _detect_document_type(self, raw_text: str, structured_tests: List[Dict[str, Any]]) -> str:
        lowered = raw_text.lower()

        if any(keyword in lowered for keyword in ["x-ray", "mri", "ct", "ultrasound", "impression", "findings"]):
            return "radiology_report"
        if any(keyword in lowered for keyword in ["discharge summary", "chief complaint", "hospital course", "discharge diagnosis"]):
            return "discharge_summary"
        if any(keyword in lowered for keyword in ["prescription", "tablet", "capsule", "dosage", "take one", "rx"]):
            return "prescription_document"
        if structured_tests:
            return "lab_report"
        return "general_medical_report"

    def _extract_entity_names(self, nlp_result: Dict[str, Any]) -> List[str]:
        entity_names: List[str] = []
        for entity in nlp_result.get("entities", []):
            text = entity.get("text", "").strip()
            if text and text not in entity_names:
                entity_names.append(text)
        return entity_names[:20]

    def _select_glossary_terms(self, nlp_result: Dict[str, Any]) -> List[str]:
        preferred_labels = {"CHEMICAL", "DISEASE", "TEST_NAME", "MEDICATION", "CONDITION", "ANATOMY"}
        terms: List[str] = []
        for entity in nlp_result.get("entities", []):
            if entity.get("label") not in preferred_labels:
                continue
            text = entity.get("text", "").strip()
            if len(text) < 3 or text.lower() in {"normal", "high", "low"}:
                continue
            if text not in terms:
                terms.append(text)
        return terms[:10]

    def _build_narrative_summary(self, explanation: str) -> str:
        sentences = re.split(r"(?<=[.!?])\s+", explanation.strip())
        return " ".join(sentences[:3]).strip() if explanation.strip() else ""

    def _flatten_simplified_text(self, simplified_output: Dict[str, Any]) -> str:
        parts = [simplified_output.get("summary", ""), simplified_output.get("report_explanation", "")]
        for test in simplified_output.get("tests", []):
            parts.append(test.get("explanation", ""))
        parts.extend(simplified_output.get("glossary", {}).values())
        return "\n".join(part for part in parts if part).strip()

    def _build_follow_up_questions(
        self,
        *,
        document_type: str,
        abnormal_tests: List[Dict[str, Any]],
    ) -> List[str]:
        if abnormal_tests:
            top_abnormal = abnormal_tests[0]["test_name"]
            return [
                f"What could be causing my {top_abnormal} result to be outside the normal range?",
                "Do I need repeat testing or any additional investigations?",
                "Are there lifestyle changes or medicines I should discuss with you?",
            ]

        prompts_by_type = {
            "radiology_report": [
                "What do the findings and impression mean in plain language?",
                "Is any follow-up imaging or specialist consultation needed?",
                "Which symptoms should make me seek care sooner?",
            ],
            "discharge_summary": [
                "Which diagnoses or hospital findings matter most for me now?",
                "What medicines, restrictions, or follow-up visits should I prioritize?",
                "What warning signs should bring me back to the hospital?",
            ],
            "prescription_document": [
                "What is each medicine for, and how should I take it safely?",
                "Are there important side effects or interactions I should watch for?",
                "When should I follow up if my symptoms do not improve?",
            ],
        }
        return prompts_by_type.get(
            document_type,
            [
                "What are the most important things I should understand from this report?",
                "Do I need any follow-up tests or appointments?",
                "What symptoms or changes should I monitor after this report?",
            ],
        )

    def _build_visual_overlays(
        self,
        *,
        layout_pages: List[Dict[str, Any]],
        entities: List[Dict[str, Any]],
        abnormal_tests: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        abnormal_names = {
            test.get("test_name", "").strip().lower()
            for test in abnormal_tests
            if test.get("test_name")
        }
        overlays: List[Dict[str, Any]] = []

        for page in layout_pages:
            highlights = []
            words = page.get("words", [])
            if words:
                for entity in entities:
                    matching_words = [
                        word
                        for word in words
                        if word.get("start", -1) < entity.get("end", -1)
                        and word.get("end", -1) > entity.get("start", -1)
                    ]
                    if not matching_words:
                        continue

                    x = min(word["x"] for word in matching_words)
                    y = min(word["y"] for word in matching_words)
                    max_x = max(word["x"] + word["width"] for word in matching_words)
                    max_y = max(word["y"] + word["height"] for word in matching_words)
                    label = entity.get("label", "ENTITY")
                    is_abnormal = entity.get("text", "").strip().lower() in abnormal_names
                    highlights.append(
                        {
                            "text": entity.get("text", ""),
                            "label": label,
                            "x": x,
                            "y": y,
                            "width": max_x - x,
                            "height": max_y - y,
                            "style": "abnormal" if is_abnormal else "entity",
                        }
                    )

            overlays.append(
                {
                    "page_number": page.get("page_number"),
                    "width": page.get("width"),
                    "height": page.get("height"),
                    "preview_available": page.get("preview_available", False),
                    "highlight_count": len(highlights),
                    "highlights": highlights,
                }
            )

        return overlays
