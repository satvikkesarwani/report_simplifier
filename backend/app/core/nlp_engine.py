import re
from typing import Any, Dict, List, Optional

try:
    import spacy
    from spacy.matcher import Matcher
except Exception:
    spacy = None
    Matcher = None

from app.config import get_settings

settings = get_settings()


SECTION_HEADERS = {
    "impression": "impression",
    "findings": "findings",
    "conclusion": "conclusion",
    "opinion": "conclusion",
    "advice": "advice",
    "history": "history",
    "medications": "medications",
    "prescription": "medications",
    "diagnosis": "diagnosis",
    "discharge diagnosis": "diagnosis",
    "hospital course": "hospital_course",
    "chief complaint": "chief_complaint",
}

CONDITION_TERMS = [
    "anemia",
    "infection",
    "inflammation",
    "diabetes",
    "hypertension",
    "hypothyroidism",
    "hyperthyroidism",
    "hepatitis",
    "fatty liver",
    "jaundice",
    "pneumonia",
    "fracture",
    "effusion",
    "edema",
    "lesion",
    "mass",
    "calcification",
    "obstruction",
    "stone",
    "tumor",
]

ANATOMY_TERMS = [
    "brain",
    "lung",
    "lungs",
    "liver",
    "kidney",
    "kidneys",
    "heart",
    "thyroid",
    "abdomen",
    "pelvis",
    "chest",
    "spine",
    "gallbladder",
    "pancreas",
    "spleen",
    "urinary bladder",
]

MEDICATION_FORMS = [
    "tablet",
    "capsule",
    "syrup",
    "injection",
    "drops",
    "cream",
    "ointment",
]

TEST_TERMS = [
    "cbc",
    "complete blood count",
    "hemoglobin",
    "wbc",
    "rbc",
    "platelet",
    "creatinine",
    "bilirubin",
    "glucose",
    "cholesterol",
    "hdl",
    "ldl",
    "triglycerides",
    "tsh",
    "t3",
    "t4",
    "hba1c",
    "a1c",
    "sgpt",
    "sgot",
]


class NLPEngine:
    """Medical NLP engine with spaCy/SciSpacy plus report-specific rule extraction."""

    def __init__(self):
        self.nlp = None
        self.matcher = None
        self.active_model = "unavailable"
        self.backend = "uninitialized"
        self._load_model()
        self._setup_patterns()

    def _load_model(self):
        if spacy is None:
            self.nlp = None
            self.matcher = None
            self.active_model = "none"
            self.backend = "regex-only"
            return
        if settings.SPACY_MODEL_PATH:
            try:
                self.nlp = spacy.load(settings.SPACY_MODEL_PATH, disable=["parser", "lemmatizer"])
                self.active_model = settings.SPACY_MODEL_PATH
                self.backend = "spacy-path"
                return
            except OSError:
                pass
        try:
            self.nlp = spacy.load(settings.SPACY_MODEL, disable=["parser", "lemmatizer"])
            self.active_model = settings.SPACY_MODEL
            self.backend = "scispacy"
        except OSError:
            try:
                self.nlp = spacy.load(
                    settings.FALLBACK_SPACY_MODEL,
                    disable=["parser", "lemmatizer", "attribute_ruler"],
                )
                self.active_model = settings.FALLBACK_SPACY_MODEL
                self.backend = "spacy-fallback"
            except OSError:
                raise RuntimeError(
                    "No spaCy model available. Run: python -m spacy download en_core_web_sm"
                )

        self.matcher = Matcher(self.nlp.vocab)

    def _setup_patterns(self):
        if self.matcher is None:
            return
        test_patterns = [
            [{"LOWER": {"IN": ["cbc", "complete", "blood", "count"]}}],
            [{"LOWER": {"IN": ["lft", "liver", "function"]}}],
            [{"LOWER": {"IN": ["rft", "renal", "kidney", "function"]}}],
            [{"LOWER": {"IN": ["lipid", "profile"]}}],
            [{"LOWER": "hb"}, {"IS_PUNCT": True, "OP": "?"}],
            [{"LOWER": {"IN": ["hemoglobin", "haemoglobin"]}}],
            [{"LOWER": {"IN": ["wbc", "tlc", "total", "leukocyte"]}}],
            [{"LOWER": {"IN": ["rbc", "red", "blood", "cell"]}}],
            [{"LOWER": {"IN": ["platelet", "plt"]}}],
            [{"LOWER": {"IN": ["mcv", "mch", "mchc", "pcv", "hct"]}}],
            [{"LOWER": {"IN": ["sgpt", "alt", "sgot", "ast", "alp", "ggt"]}}],
            [{"LOWER": {"IN": ["bilirubin", "creatinine", "urea", "sugar", "glucose"]}}],
            [{"LOWER": {"IN": ["sodium", "potassium", "chloride", "calcium"]}}],
            [{"LOWER": {"IN": ["cholesterol", "triglycerides", "hdl", "ldl", "vldl"]}}],
            [{"LOWER": {"IN": ["tsh", "t3", "t4", "thyroid"]}}],
            [{"LOWER": {"IN": ["esr", "crp", "ra", "factor", "hba1c", "a1c"]}}],
            [{"LOWER": {"IN": ["uric", "acid", "vitamin", "ferritin", "folate"]}}],
        ]
        condition_patterns = [[{"LOWER": term}] for term in sorted(set(CONDITION_TERMS))]
        anatomy_patterns = [[{"LOWER": term}] for term in sorted(set(ANATOMY_TERMS))]
        medication_patterns = [
            [{"IS_ALPHA": True, "OP": "+"}, {"LOWER": {"IN": MEDICATION_FORMS}}],
            [{"LOWER": {"IN": MEDICATION_FORMS}}, {"IS_ALPHA": True, "OP": "+"}],
        ]

        self.matcher.add("TEST_NAME", test_patterns)
        self.matcher.add("CONDITION", condition_patterns)
        self.matcher.add("ANATOMY", anatomy_patterns)
        self.matcher.add("MEDICATION", medication_patterns)

    def process_text(self, text: str) -> Dict[str, Any]:
        doc = self.nlp(text) if self.nlp is not None else None
        sections = self._segment_sections(text)
        entities = self._extract_entities(doc, text)
        values = self._extract_values(text)
        ranges = self._extract_reference_ranges(text)
        structured_tests = self._associate_tests_values(entities, values, ranges, text)

        for test in structured_tests:
            test["status"] = self._classify_abnormality(test)
            test["risk_level"] = self._calculate_risk(test)

        narrative_findings = self._extract_narrative_findings(text, sections)
        medications = [entity for entity in entities if entity["label"] == "MEDICATION"]
        conditions = [entity for entity in entities if entity["label"] == "CONDITION"]
        anatomy = [entity for entity in entities if entity["label"] == "ANATOMY"]

        return {
            "raw_text": text,
            "sections": sections,
            "entities": entities,
            "extracted_values": values,
            "structured_tests": structured_tests,
            "narrative_findings": narrative_findings,
            "medications": medications,
            "conditions": conditions,
            "anatomy": anatomy,
            "abnormal_count": sum(
                1 for test in structured_tests if test["status"] not in ["NORMAL", "UNKNOWN"]
            ),
        }

    def _segment_sections(self, text: str) -> Dict[str, str]:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        current_section = "body"
        sections: Dict[str, List[str]] = {"body": []}

        for line in lines:
            normalized = re.sub(r"[:\s]+$", "", line.lower())
            mapped_header = SECTION_HEADERS.get(normalized)
            if mapped_header:
                current_section = mapped_header
                sections.setdefault(current_section, [])
                continue
            sections.setdefault(current_section, []).append(line)

        return {name: "\n".join(values).strip() for name, values in sections.items() if values}

    def _extract_entities(self, doc, text: str) -> List[Dict[str, Any]]:
        entities: List[Dict[str, Any]] = []

        if doc is not None:
            for ent in doc.ents:
                entities.append(
                    {
                        "text": ent.text,
                        "label": self._normalize_spacy_label(ent.label_),
                        "start": ent.start_char,
                        "end": ent.end_char,
                        "source": "scispacy",
                    }
                )

            matches = self.matcher(doc) if self.matcher is not None else []
            for match_id, start, end in matches:
                span = doc[start:end]
                label = self.nlp.vocab.strings[match_id]
                entities.append(
                    {
                        "text": span.text,
                        "label": label,
                        "start": span.start_char,
                        "end": span.end_char,
                        "source": "custom_matcher",
                    }
                )
        else:
            entities.extend(self._extract_regex_entities(text, "CONDITION", CONDITION_TERMS))
            entities.extend(self._extract_regex_entities(text, "ANATOMY", ANATOMY_TERMS))
            entities.extend(self._extract_regex_entities(text, "TEST_NAME", TEST_TERMS))

        entities.extend(self._extract_medication_mentions(text))
        return self._deduplicate_entities(entities)

    def _extract_regex_entities(self, text: str, label: str, terms: List[str]) -> List[Dict[str, Any]]:
        entities = []
        for term in sorted(set(terms), key=len, reverse=True):
            for match in re.finditer(rf"\b{re.escape(term)}\b", text, re.IGNORECASE):
                entities.append(
                    {
                        "text": match.group(0),
                        "label": label,
                        "start": match.start(),
                        "end": match.end(),
                        "source": "regex",
                    }
                )
        return entities

    def _normalize_spacy_label(self, label: str) -> str:
        mapping = {
            "CHEMICAL": "TEST_NAME",
            "DISEASE": "CONDITION",
            "DISEASE_OR_SYNDROME": "CONDITION",
            "BODY_PART_OR_ORGAN_COMPONENT": "ANATOMY",
        }
        return mapping.get(label, label)

    def _deduplicate_entities(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        seen = set()
        unique = []
        for entity in entities:
            key = (entity["label"], entity["start"], entity["end"], entity["text"].lower())
            if key in seen:
                continue
            seen.add(key)
            unique.append(entity)
        unique.sort(key=lambda item: (item["start"], item["end"]))
        return unique

    def _extract_medication_mentions(self, text: str) -> List[Dict[str, Any]]:
        matches = []
        pattern = re.compile(
            r"\b([A-Z][A-Za-z0-9-]+(?:\s+[A-Z][A-Za-z0-9-]+)?)\s+"
            r"(tablet|capsule|syrup|injection|drops|cream|ointment)\b",
            re.IGNORECASE,
        )
        for match in pattern.finditer(text):
            matches.append(
                {
                    "text": match.group(0),
                    "label": "MEDICATION",
                    "start": match.start(),
                    "end": match.end(),
                    "source": "regex",
                }
            )
        return matches

    def _extract_values(self, text: str) -> List[Dict[str, Any]]:
        values = []
        patterns = [
            r"(\d{1,3}(?:,\d{3})*\.?\d*)\s*(g/dL|mg/dL|U/L|/µL|/uL|mmol/L|µmol/L|fL|pg|%|million/µL|thousand/µL|mg/L|ng/mL|mL|dL|L|mm|cm|kg|g|mg|mcg|IU|mmHg|cells/uL)",
            r"(\d+\.?\d*)\s*(x?10\^\d+|×10\^\d+|e\d+)",
        ]
        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                values.append(
                    {
                        "value": match.group(1).replace(",", ""),
                        "unit": match.group(2).lower() if match.group(2) else "",
                        "position": match.start(),
                        "text": match.group(0),
                    }
                )
        return values

    def _extract_reference_ranges(self, text: str) -> List[Dict[str, Any]]:
        ranges = []
        range_patterns = [
            r"(?:normal|reference|range)[\s:]*(?:value[s]?[\s:]*?)?(\d+\.?\d*)\s*[-–to]+\s*(\d+\.?\d+)",
            r"\((\d+\.?\d*)\s*[-–]\s*(\d+\.?\d*)\)",
            r"(\d+\.?\d*)\s*[-–]\s*(\d+\.?\d*)\s*(g/dL|mg/dL|U/L|/µL|mmol/L|fL|pg|%|million/µL|thousand/µL)",
        ]
        for pattern in range_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                ranges.append(
                    {
                        "min": float(match.group(1)),
                        "max": float(match.group(2)),
                        "unit": match.group(3).lower()
                        if len(match.groups()) > 2 and match.group(3)
                        else "",
                        "position": match.start(),
                        "text": match.group(0),
                    }
                )
        return ranges

    def _associate_tests_values(
        self,
        entities: List[Dict[str, Any]],
        values: List[Dict[str, Any]],
        ranges: List[Dict[str, Any]],
        text: str,
    ) -> List[Dict[str, Any]]:
        tests = []
        test_entities = [entity for entity in entities if entity["label"] in {"TEST_NAME", "CHEMICAL"}]

        for value in values:
            value_pos = value["position"]
            nearest_test = None
            nearest_distance = float("inf")

            for entity in test_entities:
                if entity["end"] <= value_pos:
                    distance = value_pos - entity["end"]
                    if distance < nearest_distance and distance < 200:
                        nearest_distance = distance
                        nearest_test = entity

            nearest_range = None
            nearest_range_distance = float("inf")
            for range_info in ranges:
                distance = abs(range_info["position"] - value_pos)
                if distance < nearest_range_distance and distance < 300:
                    nearest_range_distance = distance
                    nearest_range = range_info

            nearby_text = text[max(0, value_pos - 50) : value_pos + 50]
            tests.append(
                {
                    "test_name": nearest_test["text"] if nearest_test else "Unknown Test",
                    "value": value["value"],
                    "unit": value["unit"],
                    "normal_range": nearest_range,
                    "status_hint": self._detect_status_hints(nearby_text),
                    "position": value_pos,
                    "confidence": 0.9 if nearest_test else 0.5,
                }
            )

        return tests

    def _extract_narrative_findings(self, text: str, sections: Dict[str, str]) -> List[Dict[str, Any]]:
        findings = []
        for section_name in ("impression", "findings", "conclusion", "diagnosis", "hospital_course"):
            content = sections.get(section_name)
            if not content:
                continue
            for sentence in re.split(r"(?<=[.!?])\s+", content):
                cleaned = sentence.strip()
                if len(cleaned) < 12:
                    continue
                findings.append({"section": section_name, "text": cleaned})

        if not findings:
            for sentence in re.split(r"(?<=[.!?])\s+", text):
                cleaned = sentence.strip()
                if any(term in cleaned.lower() for term in CONDITION_TERMS + ANATOMY_TERMS):
                    findings.append({"section": "body", "text": cleaned})
                if len(findings) >= 8:
                    break

        return findings[:12]

    def _detect_status_hints(self, text: str) -> Optional[str]:
        text_upper = text.upper()
        high_indicators = ["HIGH", "H", "↑", "ELEVATED", "INCREASED", "ABOVE"]
        low_indicators = ["LOW", "L", "↓", "DECREASED", "BELOW", "REDUCED"]
        for indicator in high_indicators:
            if indicator in text_upper:
                return "HIGH"
        for indicator in low_indicators:
            if indicator in text_upper:
                return "LOW"
        return None

    def _classify_abnormality(self, test: Dict[str, Any]) -> str:
        try:
            value = float(test["value"])
        except (ValueError, TypeError):
            if test.get("status_hint"):
                return test["status_hint"]
            return "UNKNOWN"

        range_info = test.get("normal_range")
        if not range_info:
            if test.get("status_hint"):
                return test["status_hint"]
            return "UNKNOWN"

        min_value = range_info.get("min")
        max_value = range_info.get("max")
        if min_value is None or max_value is None:
            return "UNKNOWN"

        border_low = min_value * 0.95
        border_high = max_value * 1.05

        if value < min_value:
            if value < border_low:
                return "LOW"
            return "BORDERLINE_LOW"
        if value > max_value:
            if value > border_high:
                return "HIGH"
            return "BORDERLINE_HIGH"
        return "NORMAL"

    def _calculate_risk(self, test: Dict[str, Any]) -> int:
        status = test.get("status", "UNKNOWN")
        risk_map = {
            "NORMAL": 1,
            "BORDERLINE_LOW": 2,
            "BORDERLINE_HIGH": 2,
            "LOW": 3,
            "HIGH": 3,
            "CRITICAL_LOW": 5,
            "CRITICAL_HIGH": 5,
            "UNKNOWN": 1,
        }
        base_risk = risk_map.get(status, 1)

        try:
            value = float(test["value"])
            range_info = test.get("normal_range")
            if range_info:
                min_value = range_info.get("min", value)
                max_value = range_info.get("max", value)
                midpoint = (min_value + max_value) / 2

                if status in ["LOW", "BORDERLINE_LOW"]:
                    deviation = (midpoint - value) / max(midpoint, 1e-9)
                    if deviation > 0.5:
                        base_risk = min(5, base_risk + 2)
                    elif deviation > 0.3:
                        base_risk = min(5, base_risk + 1)
                elif status in ["HIGH", "BORDERLINE_HIGH"]:
                    deviation = (value - midpoint) / max(midpoint, 1e-9)
                    if deviation > 0.5:
                        base_risk = min(5, base_risk + 2)
                    elif deviation > 0.3:
                        base_risk = min(5, base_risk + 1)
        except (ValueError, TypeError):
            pass

        return base_risk
