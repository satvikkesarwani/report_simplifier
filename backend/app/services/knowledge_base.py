import json
import os
import re
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from html import unescape
from html.parser import HTMLParser
from typing import Dict, Iterable, List

from app.config import get_settings

settings = get_settings()
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}


DEFAULT_TESTING_GUIDES = [
    "https://www.testing.com/tests/",
]


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts: List[str] = []

    def handle_data(self, data: str):
        cleaned = data.strip()
        if cleaned:
            self.parts.append(cleaned)

    def text(self) -> str:
        return " ".join(self.parts)


@dataclass
class SourceDocument:
    title: str
    source: str
    url: str
    category: str
    text: str


class KnowledgeBaseBuilder:
    def __init__(self):
        self.base_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", settings.KNOWLEDGE_BASE_DIR)
        )
        self.chunks_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", settings.KNOWLEDGE_BASE_CHUNKS_PATH)
        )
        self.manifest_path = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                "..",
                "..",
                settings.KNOWLEDGE_BASE_SOURCE_MANIFEST,
            )
        )

    def ensure_manifest(self) -> Dict[str, List[str]]:
        os.makedirs(os.path.dirname(self.manifest_path), exist_ok=True)
        if os.path.exists(self.manifest_path):
            with open(self.manifest_path, "r", encoding="utf-8") as handle:
                return json.load(handle)

        manifest = {
            "medlineplus_xml": ["https://medlineplus.gov/xml.html"],
            "testing_guides": DEFAULT_TESTING_GUIDES,
        }
        with open(self.manifest_path, "w", encoding="utf-8") as handle:
            json.dump(manifest, handle, indent=2)
        return manifest

    def build_chunks_from_sources(self) -> List[Dict[str, str]]:
        manifest = self.ensure_manifest()
        documents: List[SourceDocument] = []

        for url in manifest.get("medlineplus_xml", []):
            documents.extend(self._fetch_medlineplus_documents(url))

        for url in manifest.get("testing_guides", []):
            for guide_url in self._expand_testing_urls(url):
                try:
                    documents.append(self._fetch_testing_guide(guide_url))
                except Exception:
                    continue

        chunks = self._chunk_documents(documents)
        os.makedirs(os.path.dirname(self.chunks_path), exist_ok=True)
        with open(self.chunks_path, "w", encoding="utf-8") as handle:
            json.dump(chunks, handle, indent=2)
        return chunks

    def _fetch_medlineplus_documents(self, url: str) -> List[SourceDocument]:
        if url.endswith("/xml.html") or url.endswith("xml.html"):
            url = self._resolve_latest_medlineplus_xml_url(url)
        with _urlopen(url, timeout=60) as response:
            xml_content = response.read()

        root = ET.fromstring(xml_content)
        documents = []
        for topic in root.findall(".//health-topic"):
            title = topic.attrib.get("title") or topic.findtext("title") or "Untitled Topic"
            summary = "".join(topic.findtext("full-summary", default=""))
            topic_url = topic.attrib.get("url", url)
            summary = _clean_html(summary)
            if not summary:
                continue
            documents.append(
                SourceDocument(
                    title=title,
                    source="MedlinePlus",
                    url=topic_url,
                    category="health_topic",
                    text=summary,
                )
            )
        return documents

    def _resolve_latest_medlineplus_xml_url(self, index_url: str) -> str:
        with _urlopen(index_url, timeout=60) as response:
            html = response.read().decode("utf-8", errors="ignore")

        match = re.search(r"https://medlineplus\.gov/xml/mplus_topics_[0-9-]+\.xml", html)
        if match:
            return match.group(0)

        relative_match = re.search(r"/xml/mplus_topics_[0-9-]+\.xml", html)
        if relative_match:
            return f"https://medlineplus.gov{relative_match.group(0)}"

        raise RuntimeError("Could not resolve the latest MedlinePlus XML file URL.")

    def _fetch_testing_guide(self, url: str) -> SourceDocument:
        with _urlopen(url, timeout=60) as response:
            html = response.read().decode("utf-8", errors="ignore")

        title_match = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
        title = unescape(title_match.group(1)).strip() if title_match else url.rstrip("/").split("/")[-1]
        content = _clean_html(html)
        return SourceDocument(
            title=title,
            source="Testing.com",
            url=url,
            category="lab_test_guide",
            text=content,
        )

    def _expand_testing_urls(self, url: str) -> List[str]:
        if not url.rstrip("/").endswith("/tests"):
            return [url]

        with _urlopen(url, timeout=60) as response:
            html = response.read().decode("utf-8", errors="ignore")

        matches = re.findall(r"https://www\.testing\.com/tests/[a-z0-9-]+/?", html)
        if not matches:
            matches = re.findall(r"/tests/[a-z0-9-]+/?", html)
            matches = [f"https://www.testing.com{match}" for match in matches]

        unique = []
        seen = set()
        for match in matches:
            normalized = match.rstrip("/") + "/"
            if normalized == "https://www.testing.com/tests/" or normalized in seen:
                continue
            seen.add(normalized)
            unique.append(normalized)
        return unique[:400]

    def _chunk_documents(self, documents: Iterable[SourceDocument]) -> List[Dict[str, str]]:
        chunks = []
        chunk_size = max(settings.CHUNK_SIZE, 200)
        overlap = min(settings.CHUNK_OVERLAP, chunk_size // 4)

        for document in documents:
            words = document.text.split()
            if not words:
                continue

            start = 0
            chunk_index = 0
            while start < len(words):
                end = min(start + chunk_size, len(words))
                chunk_text = " ".join(words[start:end]).strip()
                if len(chunk_text.split()) < 40:
                    break
                chunks.append(
                    {
                        "text": chunk_text,
                        "source": document.source,
                        "title": document.title,
                        "category": document.category,
                        "url": document.url,
                        "chunk_index": chunk_index,
                    }
                )
                chunk_index += 1
                if end == len(words):
                    break
                start = max(end - overlap, start + 1)
        return chunks


def _clean_html(raw_text: str) -> str:
    parser = _TextExtractor()
    parser.feed(raw_text)
    text = parser.text()
    text = unescape(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _urlopen(url: str, timeout: int = 60):
    request = urllib.request.Request(url, headers=DEFAULT_HEADERS)
    return urllib.request.urlopen(request, timeout=timeout)
