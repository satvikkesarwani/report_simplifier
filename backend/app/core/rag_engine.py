import json
import os
import re
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
from sklearn.feature_extraction.text import HashingVectorizer

from app.config import get_settings
from app.services.knowledge_base import KnowledgeBaseBuilder

settings = get_settings()


class RAGEngine:
    """Retrieval-Augmented Generation engine using FAISS + sentence transformers."""

    def __init__(self):
        self.embedding_model = None
        self.embedding_backend = "uninitialized"
        self.index = None
        self.id_to_chunk = {}
        self.lexical_chunks = []
        self._load_embedding_model()
        self._load_or_build_index()

    def _load_embedding_model(self):
        if self.embedding_model is None:
            if settings.EMBEDDING_MODEL_PATH:
                try:
                    from sentence_transformers import SentenceTransformer

                    self.embedding_model = SentenceTransformer(
                        settings.EMBEDDING_MODEL_PATH,
                        local_files_only=True,
                    )
                    self.embedding_backend = "sentence-transformers-path"
                    return
                except Exception:
                    pass
            if not self._sentence_transformer_cached():
                self.embedding_model = HashingVectorizer(
                    n_features=settings.EMBEDDING_DIM,
                    alternate_sign=False,
                    norm=None,
                )
                self.embedding_backend = "hashing-vectorizer"
                return
            try:
                from sentence_transformers import SentenceTransformer

                self.embedding_model = SentenceTransformer(
                    settings.EMBEDDING_MODEL,
                    local_files_only=True,
                )
                self.embedding_backend = "sentence-transformers"
            except Exception:
                self.embedding_model = HashingVectorizer(
                    n_features=settings.EMBEDDING_DIM,
                    alternate_sign=False,
                    norm=None,
                )
                self.embedding_backend = "hashing-vectorizer"

    def _load_or_build_index(self):
        index_path = os.path.join(settings.FAISS_INDEX_PATH, "medical_kb.index")
        mapping_path = os.path.join(settings.FAISS_INDEX_PATH, "id_mapping.json")

        if os.path.exists(index_path) and os.path.exists(mapping_path):
            try:
                import faiss

                self.index = faiss.read_index(index_path)
                with open(mapping_path, "r", encoding="utf-8") as handle:
                    self.id_to_chunk = json.load(handle)
            except Exception:
                self.index = None
                self._load_chunks_only()
        else:
            self._build_index()

    def rebuild_index(self):
        self._build_index()

    def _build_index(self):
        chunks_path = settings.KNOWLEDGE_BASE_CHUNKS_PATH
        if not os.path.isabs(chunks_path):
            chunks_path = os.path.normpath(os.path.join(os.getcwd(), chunks_path))

        if not os.path.exists(chunks_path):
            try:
                KnowledgeBaseBuilder().build_chunks_from_sources()
            except Exception:
                self._create_default_kb(chunks_path)

        with open(chunks_path, "r", encoding="utf-8") as handle:
            chunks = json.load(handle)
        self.lexical_chunks = chunks

        try:
            import faiss
        except Exception:
            self.index = None
            self.id_to_chunk = {str(index): chunks[index] for index in range(len(chunks))}
            return

        texts = [chunk["text"] for chunk in chunks]
        embeddings = self._encode_texts(texts)
        dim = settings.EMBEDDING_DIM

        nlist = min(4096, max(1, len(chunks) // 39 + 1))
        quantizer = faiss.IndexFlatIP(dim)
        self.index = faiss.IndexIVFFlat(quantizer, dim, nlist, faiss.METRIC_INNER_PRODUCT)
        faiss.normalize_L2(embeddings)
        self.index.train(embeddings)
        self.index.add(embeddings)
        self.index.nprobe = min(64, max(1, nlist))
        self.id_to_chunk = {str(index): chunks[index] for index in range(len(chunks))}

        os.makedirs(settings.FAISS_INDEX_PATH, exist_ok=True)
        faiss.write_index(self.index, os.path.join(settings.FAISS_INDEX_PATH, "medical_kb.index"))
        with open(os.path.join(settings.FAISS_INDEX_PATH, "id_mapping.json"), "w", encoding="utf-8") as handle:
            json.dump(self.id_to_chunk, handle)

    def _load_chunks_only(self):
        chunks_path = settings.KNOWLEDGE_BASE_CHUNKS_PATH
        if not os.path.isabs(chunks_path):
            chunks_path = os.path.normpath(os.path.join(os.getcwd(), chunks_path))
        if os.path.exists(chunks_path):
            with open(chunks_path, "r", encoding="utf-8") as handle:
                self.lexical_chunks = json.load(handle)
            self.id_to_chunk = {str(index): self.lexical_chunks[index] for index in range(len(self.lexical_chunks))}

    def _create_default_kb(self, chunks_path: str):
        default_chunks = [
            {
                "text": "Hemoglobin (Hb) is a protein in red blood cells that carries oxygen throughout your body. Normal range for men is 13.0 to 17.0 g/dL. Normal range for women is 12.0 to 15.5 g/dL. Low hemoglobin may indicate anemia, blood loss, or nutritional deficiencies like iron, B12, or folate. High hemoglobin may indicate dehydration, lung disease, or bone marrow disorders.",
                "source": "fallback",
                "title": "Hemoglobin Test",
                "category": "blood_test",
                "url": "",
            },
            {
                "text": "White Blood Cell Count (WBC or TLC) measures the number of white blood cells that fight infection. Normal range is 4,500 to 11,000 cells per microliter. High WBC may indicate infection, inflammation, stress, or leukemia. Low WBC may indicate bone marrow problems, autoimmune disorders, or medication side effects.",
                "source": "fallback",
                "title": "WBC Count",
                "category": "blood_test",
                "url": "",
            },
            {
                "text": "Creatinine measures kidney function waste product. Normal is about 0.7 to 1.3 mg/dL for men and 0.6 to 1.1 mg/dL for women. High creatinine indicates impaired kidney function, dehydration, or urinary obstruction.",
                "source": "fallback",
                "title": "Creatinine",
                "category": "blood_test",
                "url": "",
            },
        ]
        os.makedirs(os.path.dirname(chunks_path), exist_ok=True)
        with open(chunks_path, "w", encoding="utf-8") as handle:
            json.dump(default_chunks, handle, indent=2)

    def search(self, query: str, k: Optional[int] = None, threshold: Optional[float] = None) -> List[Dict]:
        if k is None:
            k = settings.TOP_K_RETRIEVAL
        if threshold is None:
            threshold = settings.SIMILARITY_THRESHOLD

        if self.index is None or self.embedding_model is None:
            return self._lexical_search(query, k=k)

        import faiss

        query_embedding = self._encode_texts([query])
        faiss.normalize_L2(query_embedding)
        distances, indices = self.index.search(query_embedding, k)

        results = []
        for rank, (distance, idx) in enumerate(zip(distances[0], indices[0]), start=1):
            if idx == -1 or distance < threshold:
                continue
            chunk = self.id_to_chunk.get(str(int(idx)))
            if not chunk:
                continue
            results.append(
                {
                    "text": chunk["text"],
                    "source": chunk.get("source", "unknown"),
                    "title": chunk.get("title", ""),
                    "category": chunk.get("category", ""),
                    "score": float(distance),
                    "rank": rank,
                    "url": chunk.get("url", ""),
                }
            )
        if not results and self.embedding_backend == "hashing-vectorizer":
            for rank, (distance, idx) in enumerate(zip(distances[0], indices[0]), start=1):
                if idx == -1:
                    continue
                chunk = self.id_to_chunk.get(str(int(idx)))
                if not chunk:
                    continue
                results.append(
                    {
                        "text": chunk["text"],
                        "source": chunk.get("source", "unknown"),
                        "title": chunk.get("title", ""),
                        "category": chunk.get("category", ""),
                        "score": float(distance),
                        "rank": rank,
                        "url": chunk.get("url", ""),
                    }
                )
        return results

    def _lexical_search(self, query: str, k: int) -> List[Dict]:
        query_terms = {term for term in query.lower().split() if len(term) > 2}
        scored = []
        for chunk in self.lexical_chunks:
            chunk_terms = set(chunk["text"].lower().split())
            overlap = len(query_terms & chunk_terms)
            if overlap == 0:
                continue
            scored.append(
                (
                    overlap / max(len(query_terms), 1),
                    {
                        "text": chunk["text"],
                        "source": chunk.get("source", "unknown"),
                        "title": chunk.get("title", ""),
                        "category": chunk.get("category", ""),
                        "score": overlap / max(len(query_terms), 1),
                        "url": chunk.get("url", ""),
                    },
                )
            )
        scored.sort(key=lambda item: item[0], reverse=True)
        results = []
        for rank, (_, payload) in enumerate(scored[:k], start=1):
            payload["rank"] = rank
            results.append(payload)
        return results

    def retrieve_for_test(self, test_name: str, value: str = "", status: str = "") -> List[Dict]:
        queries = [
            f"{test_name} test what it measures normal range",
            f"{test_name} {status} means",
            f"{test_name} medical test explanation {value}",
        ]
        all_results = []
        seen_texts = set()
        for query in queries:
            for result in self.search(query, k=2):
                if result["text"] in seen_texts:
                    continue
                seen_texts.add(result["text"])
                all_results.append(result)
        all_results.sort(key=lambda item: item["score"], reverse=True)
        return all_results[: settings.TOP_K_RETRIEVAL]

    def format_context(self, results: List[Dict]) -> str:
        if not results:
            return "No specific medical knowledge retrieved for this test."
        snippets = []
        for result in results[:2]:
            title = result.get("title", "Medical Information")
            text = re.sub(r"\s+", " ", result["text"]).strip()
            if len(text) > 280:
                text = text[:277].rstrip() + "..."
            snippets.append(f"{title}: {text}")
        return "\n".join(snippets)

    def _encode_texts(self, texts: List[str]) -> np.ndarray:
        if self.embedding_backend == "sentence-transformers":
            # Batch in chunks of 256 to avoid loky/multiprocessing crashes
            # that occur on Python 3.13 with very large batch sizes.
            batch_size = 256
            all_embeddings = []
            for i in range(0, len(texts), batch_size):
                batch = texts[i : i + batch_size]
                embeddings = self.embedding_model.encode(
                    batch, show_progress_bar=len(texts) > 1000, batch_size=64
                )
                all_embeddings.append(np.array(embeddings))
            return np.vstack(all_embeddings).astype("float32")

        matrix = self.embedding_model.transform(texts)
        return matrix.toarray().astype("float32")

    def _sentence_transformer_cached(self) -> bool:
        if settings.EMBEDDING_MODEL_PATH and os.path.exists(settings.EMBEDDING_MODEL_PATH):
            return True
        # The HuggingFace hub stores models as models--{org}--{model}.
        # EMBEDDING_MODEL may be a short name like "all-MiniLM-L6-v2" or a
        # full org/model path like "sentence-transformers/all-MiniLM-L6-v2".
        # Convert slashes to double-dashes and look for any matching snapshot.
        model_dir = settings.EMBEDDING_MODEL.replace("/", "--")
        cache_root = Path.home() / ".cache" / "huggingface" / "hub"
        # Exact match (covers full org/model strings, e.g. "sentence-transformers/all-MiniLM-L6-v2")
        if any(cache_root.glob(f"models--{model_dir}/snapshots/*")):
            return True
        # Suffix match: handles short names stored under any org prefix
        short_name = model_dir.split("--")[-1]
        return any(cache_root.glob(f"models--*--{short_name}/snapshots/*"))
