import os
import re
from typing import Dict, List

try:
    import cv2
except Exception:
    cv2 = None

try:
    import numpy as np
except Exception:
    np = None

try:
    import pytesseract
except Exception:
    pytesseract = None

try:
    from pdf2image import convert_from_path
except Exception:
    convert_from_path = None

try:
    import pdfplumber
except Exception:
    pdfplumber = None

try:
    from pypdf import PdfReader
except Exception:
    PdfReader = None

from app.config import get_settings
from app.utils.file_handler import preview_dir_for_file, preview_path_for_page

settings = get_settings()
PAGE_BREAK = "\n\n--- Page Break ---\n\n"

if pytesseract and settings.TESSERACT_CMD:
    pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD


class OCREngine:
    """OCR pipeline with graceful fallbacks for embedded-text PDFs."""

    def __init__(self):
        self.config = "--oem 3 --psm 6 -c preserve_interword_spaces=1"
        self.fallback_config = (
            f"--oem 3 --psm 6 "
            f"-c preserve_interword_spaces=1 "
            f"-c tessedit_char_whitelist={settings.OCR_WHITELIST}"
        )

    def process_file(self, file_path: str) -> Dict:
        ext = file_path.split(".")[-1].lower()
        if ext == "pdf":
            return self._process_pdf(file_path)
        if ext in {"png", "jpg", "jpeg"}:
            return self._process_image(file_path)
        raise ValueError(f"Unsupported file type: {ext}")

    def _process_pdf(self, file_path: str) -> Dict:
        pages_text = []
        layout_pages = []

        if pdfplumber is not None:
            try:
                with pdfplumber.open(file_path) as pdf:
                    self._generate_pdf_previews(file_path, total_pages=len(pdf.pages))
                    global_offset = 0
                    for index, page in enumerate(pdf.pages[: settings.MAX_PAGES_PER_REPORT]):
                        if index > 0:
                            global_offset += len(PAGE_BREAK)
                        page_payload = self._extract_pdfplumber_page(
                            page=page,
                            file_path=file_path,
                            page_number=index + 1,
                            global_offset=global_offset,
                        )
                        text = page_payload["text"]
                        if text and text.strip():
                            pages_text.append(text.strip())
                            layout_pages.append(page_payload["layout_page"])
                            global_offset += len(text.strip())
                if pages_text:
                    return {
                        "source": "pdfplumber",
                        "pages": len(pages_text),
                        "text": PAGE_BREAK.join(pages_text),
                        "method": "embedded_text",
                        "layout_pages": layout_pages,
                    }
            except Exception:
                pages_text = []
                layout_pages = []

        if PdfReader is not None:
            try:
                self._generate_pdf_previews(file_path)
                reader = PdfReader(file_path)
                for index, page in enumerate(reader.pages[: settings.MAX_PAGES_PER_REPORT]):
                    text = page.extract_text() or ""
                    if text.strip():
                        pages_text.append(text.strip())
                        layout_pages.append(
                            {
                                "page_number": index + 1,
                                "width": 1000,
                                "height": 1400,
                                "preview_available": os.path.exists(preview_path_for_page(file_path, index + 1)),
                                "words": [],
                            }
                        )
                if pages_text:
                    return {
                        "source": "pypdf",
                        "pages": len(pages_text),
                        "text": PAGE_BREAK.join(pages_text),
                        "method": "embedded_text",
                        "layout_pages": layout_pages,
                    }
            except Exception:
                pages_text = []
                layout_pages = []

        if convert_from_path is None or pytesseract is None or cv2 is None or np is None:
            raise RuntimeError(
                "This PDF does not contain embedded text and OCR dependencies are unavailable. "
                "Install pytesseract, pdf2image, numpy, and opencv-python-headless."
            )

        try:
            images = convert_from_path(file_path, dpi=settings.OCR_DPI, fmt="jpeg")
            global_offset = 0
            for index, image in enumerate(images[: settings.MAX_PAGES_PER_REPORT]):
                page_number = index + 1
                self._save_preview_image(file_path, page_number, image)
                if index > 0:
                    global_offset += len(PAGE_BREAK)
                page_payload = self._ocr_image_array_with_layout(
                    np.array(image),
                    page_number=page_number,
                    global_offset=global_offset,
                )
                pages_text.append(page_payload["text"])
                layout_pages.append(page_payload["layout_page"])
                global_offset += len(page_payload["text"])
            return {
                "source": "tesseract_ocr",
                "pages": len(pages_text),
                "text": PAGE_BREAK.join(pages_text),
                "method": "ocr",
                "layout_pages": layout_pages,
            }
        except Exception as exc:
            raise RuntimeError(f"PDF OCR failed: {exc}")

    def _process_image(self, file_path: str) -> Dict:
        if cv2 is None or pytesseract is None or np is None:
            raise RuntimeError(
                "Image OCR dependencies are unavailable. Install pytesseract, numpy, and opencv-python-headless."
            )

        img = cv2.imread(file_path)
        if img is None:
            raise ValueError(f"Could not load image: {file_path}")

        page_payload = self._ocr_image_array_with_layout(
            img,
            page_number=1,
            global_offset=0,
            width=img.shape[1],
            height=img.shape[0],
        )
        return {
            "source": "tesseract_ocr",
            "pages": 1,
            "text": page_payload["text"],
            "method": "ocr",
            "layout_pages": [
                {
                    **page_payload["layout_page"],
                    "preview_available": True,
                }
            ],
        }

    def _preprocess_image(self, img):
        if cv2 is None or np is None:
            return img

        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img

        denoised = cv2.GaussianBlur(gray, (5, 5), 0)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(denoised)
        deskewed = self._deskew(enhanced)
        _, binary = cv2.threshold(deskewed, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return binary

    def _build_ocr_variants(self, img) -> List[tuple[str, str, object]]:
        if cv2 is None or np is None:
            return [("raw", self.config, img)]

        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img.copy()

        blurred = cv2.GaussianBlur(gray, (3, 3), 0)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)
        deskewed_gray = self._deskew(gray)
        _, binary = cv2.threshold(deskewed_gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        return [
            ("raw", self.config, img),
            ("gray", self.config, gray),
            ("deskewed-gray", self.config, deskewed_gray),
            ("clahe", self.config, clahe),
            ("binary", self.config, binary),
            ("block-raw", "--oem 3 --psm 4 -c preserve_interword_spaces=1", img),
            ("sparse-raw", "--oem 3 --psm 11 -c preserve_interword_spaces=1", img),
            ("binary-whitelist", self.fallback_config, binary),
            ("preprocessed-whitelist", self.fallback_config, self._preprocess_image(img)),
            ("blurred", self.config, blurred),
        ]

    def _candidate_text_from_data(self, data: Dict) -> str:
        parts: List[str] = []
        previous_line = None

        for index in range(len(data.get("text", []))):
            text = (data["text"][index] or "").strip()
            if not text:
                continue
            line_key = (
                data.get("block_num", [0])[index],
                data.get("par_num", [0])[index],
                data.get("line_num", [0])[index],
            )
            if previous_line is not None:
                parts.append("\n" if line_key != previous_line else " ")
            parts.append(text)
            previous_line = line_key

        return self._post_process("".join(parts))

    def _score_ocr_candidate(self, text: str, words: List[Dict], avg_confidence: float) -> float:
        if not text.strip():
            return -1e9

        alpha_tokens = re.findall(r"[A-Za-z]{3,}", text)
        numeric_tokens = re.findall(r"\d+(?:\.\d+)?", text)
        units = re.findall(r"\b(?:mg/dL|g/dL|mmol/L|IU/L|mEq/L|cells/cumm|/HPF|%)\b", text, flags=re.I)
        medical_terms = re.findall(
            r"\b(?:hemoglobin|platelet|sodium|potassium|chloride|glucose|bilirubin|albumin|globulin|urine|protein|ph|pco2|po2|crp|reactive|lymphocytes|wbc|rbc|hematology|serology)\b",
            text,
            flags=re.I,
        )
        weird_runs = re.findall(r"[A-Za-z0-9]{12,}", text)
        single_letter_lines = len(re.findall(r"(?m)^[A-Za-z0-9]$", text))

        return (
            len(alpha_tokens)
            + 3 * len(numeric_tokens)
            + 8 * len(units)
            + 12 * len(medical_terms)
            + max(avg_confidence, 0) / 10.0
            + min(len(words), 200) * 0.1
            - 8 * len(weird_runs)
            - 4 * single_letter_lines
        )

    def _run_best_ocr_pass(self, img) -> Dict:
        if pytesseract is None:
            raise RuntimeError("pytesseract is not installed.")

        best_candidate = None

        for variant_name, config, variant in self._build_ocr_variants(img):
            data = pytesseract.image_to_data(
                variant,
                config=config,
                output_type=pytesseract.Output.DICT,
                lang="eng",
            )

            words = []
            confidence_values = []
            for index in range(len(data.get("text", []))):
                text = (data["text"][index] or "").strip()
                if not text:
                    continue
                try:
                    confidence = int(float(data["conf"][index]))
                except Exception:
                    confidence = 0
                confidence_values.append(confidence)
                words.append(
                    {
                        "text": text,
                        "confidence": confidence,
                        "x": int(data["left"][index]),
                        "y": int(data["top"][index]),
                        "width": int(data["width"][index]),
                        "height": int(data["height"][index]),
                        "block_num": data.get("block_num", [0])[index],
                        "par_num": data.get("par_num", [0])[index],
                        "line_num": data.get("line_num", [0])[index],
                    }
                )

            text = self._candidate_text_from_data(data)
            avg_confidence = (
                sum(confidence_values) / len(confidence_values) if confidence_values else 0.0
            )
            candidate = {
                "variant_name": variant_name,
                "config": config,
                "text": text,
                "words": words,
                "score": self._score_ocr_candidate(text, words, avg_confidence),
            }
            if best_candidate is None or candidate["score"] > best_candidate["score"]:
                best_candidate = candidate

        return best_candidate or {
            "variant_name": "none",
            "config": self.config,
            "text": "",
            "words": [],
            "score": -1e9,
        }

    def _deskew(self, img):
        if cv2 is None or np is None:
            return img

        coords = np.column_stack(np.where(img > 0))
        if len(coords) < 100:
            return img

        angle = cv2.minAreaRect(coords)[-1]
        angle = -(90 + angle) if angle < -45 else -angle
        if abs(angle) < 0.5:
            return img

        height, width = img.shape[:2]
        center = (width // 2, height // 2)
        matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        return cv2.warpAffine(
            img,
            matrix,
            (width, height),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE,
        )

    def _ocr_image_array(self, img) -> str:
        if pytesseract is None:
            raise RuntimeError("pytesseract is not installed.")
        best = self._run_best_ocr_pass(img)
        return best["text"]

    def _ocr_image_array_with_layout(
        self,
        img,
        *,
        page_number: int,
        global_offset: int,
        width: int | None = None,
        height: int | None = None,
    ) -> Dict:
        if pytesseract is None:
            raise RuntimeError("pytesseract is not installed.")

        best = self._run_best_ocr_pass(img)
        words_data = best["words"]

        words = []
        parts: List[str] = []
        cursor = 0
        previous_line = None
        total_items = len(words_data)

        for index in range(total_items):
            text = (words_data[index]["text"] or "").strip()
            if not text:
                continue

            line_key = (
                words_data[index].get("block_num", 0),
                words_data[index].get("par_num", 0),
                words_data[index].get("line_num", 0),
            )

            separator = ""
            if previous_line is not None:
                separator = "\n" if line_key != previous_line else " "
                parts.append(separator)
                cursor += len(separator)

            start = global_offset + cursor
            parts.append(text)
            cursor += len(text)
            end = global_offset + cursor
            previous_line = line_key

            words.append(
                {
                    "text": text,
                    "confidence": words_data[index]["confidence"],
                    "start": start,
                    "end": end,
                    "x": words_data[index]["x"],
                    "y": words_data[index]["y"],
                    "width": words_data[index]["width"],
                    "height": words_data[index]["height"],
                }
            )

        page_text = best["text"] or self._post_process("".join(parts))
        page_width = width or int(getattr(img, "shape", [0, 1000])[1])
        page_height = height or int(getattr(img, "shape", [1400])[0])
        return {
            "text": page_text,
            "layout_page": {
                "page_number": page_number,
                "width": page_width,
                "height": page_height,
                "preview_available": True,
                "words": words,
                "ocr_variant": best["variant_name"],
            },
        }

    def _extract_pdfplumber_page(self, *, page, file_path: str, page_number: int, global_offset: int) -> Dict:
        raw_words = page.extract_words(use_text_flow=True) or []
        words = []
        parts: List[str] = []
        cursor = 0
        previous_top = None

        for item in raw_words:
            text = str(item.get("text", "")).strip()
            if not text:
                continue
            top = float(item.get("top", 0.0))
            separator = ""
            if previous_top is not None:
                separator = "\n" if abs(top - previous_top) > 8 else " "
                parts.append(separator)
                cursor += len(separator)

            start = global_offset + cursor
            parts.append(text)
            cursor += len(text)
            end = global_offset + cursor
            previous_top = top

            words.append(
                {
                    "text": text,
                    "confidence": 100,
                    "start": start,
                    "end": end,
                    "x": float(item.get("x0", 0.0)),
                    "y": top,
                    "width": float(item.get("x1", 0.0)) - float(item.get("x0", 0.0)),
                    "height": float(item.get("bottom", 0.0)) - top,
                }
            )

        page_text = "".join(parts).strip() or (page.extract_text() or "").strip()
        return {
            "text": page_text,
            "layout_page": {
                "page_number": page_number,
                "width": float(getattr(page, "width", 1000.0)),
                "height": float(getattr(page, "height", 1400.0)),
                "preview_available": os.path.exists(preview_path_for_page(file_path, page_number)),
                "words": words,
            },
        }

    def _generate_pdf_previews(self, file_path: str, total_pages: int | None = None) -> None:
        if convert_from_path is None:
            return

        preview_dir = preview_dir_for_file(file_path)
        os.makedirs(preview_dir, exist_ok=True)
        page_limit = min(total_pages or settings.MAX_PREVIEW_PAGES, settings.MAX_PREVIEW_PAGES)
        if page_limit <= 0:
            return

        existing = all(
            os.path.exists(preview_path_for_page(file_path, page_number))
            for page_number in range(1, page_limit + 1)
        )
        if existing:
            return

        images = convert_from_path(
            file_path,
            dpi=min(settings.OCR_DPI, 150),
            fmt="jpeg",
            first_page=1,
            last_page=page_limit,
        )
        for index, image in enumerate(images, start=1):
            self._save_preview_image(file_path, index, image)

    def _save_preview_image(self, file_path: str, page_number: int, image) -> None:
        preview_dir = preview_dir_for_file(file_path)
        os.makedirs(preview_dir, exist_ok=True)
        image.save(preview_path_for_page(file_path, page_number), format="JPEG", quality=85)

    def _post_process(self, text: str) -> str:
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]+", " ", text)
        return text.strip()

    def get_confidence_data(self, img) -> List[Dict]:
        if pytesseract is None:
            return []
        best = self._run_best_ocr_pass(img)
        return [
            {
                "text": item["text"],
                "confidence": item["confidence"],
                "x": item["x"],
                "y": item["y"],
                "width": item["width"],
                "height": item["height"],
            }
            for item in best["words"]
            if item["confidence"] > 0 and item["text"].strip()
        ]
