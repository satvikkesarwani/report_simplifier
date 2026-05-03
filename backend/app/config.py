import os
from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    APP_NAME: str = "RAG Medical Report Simplifier"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Database
    DATABASE_URL: str = "sqlite:///./medical_reports.db"
    REPORT_STORE_TABLE: str = "reports"
    
    # File Upload
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    UPLOAD_DIR: str = "./uploads"
    ALLOWED_EXTENSIONS: set = {"pdf", "png", "jpg", "jpeg"}
    
    # OCR
    TESSERACT_CMD: Optional[str] = None
    OCR_DPI: int = 300
    OCR_WHITELIST: str = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789().,/%-µ +=_°*<>[]&;:#@"
    MAX_PREVIEW_PAGES: int = 8
    
    # NLP
    SPACY_MODEL: str = "en_core_sci_lg"
    FALLBACK_SPACY_MODEL: str = "en_core_web_sm"
    SPACY_MODEL_PATH: Optional[str] = None
    
    # Embeddings & RAG
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    EMBEDDING_MODEL_PATH: Optional[str] = None
    EMBEDDING_DIM: int = 384
    FAISS_INDEX_PATH: str = "./knowledge_base/faiss_index"
    KNOWLEDGE_BASE_DIR: str = "./knowledge_base"
    KNOWLEDGE_BASE_CHUNKS_PATH: str = "./knowledge_base/chunks.json"
    KNOWLEDGE_BASE_SOURCE_MANIFEST: str = "./knowledge_base/source_manifest.json"
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 64
    TOP_K_RETRIEVAL: int = 3
    SIMILARITY_THRESHOLD: float = 0.75
    
    # LLM - NVIDIA NIM
    NVIDIA_API_KEY: Optional[str] = None
    NVIDIA_BASE_URL: str = "https://integrate.api.nvidia.com/v1"
    NVIDIA_MODEL: str = "meta/llama-3.1-70b-instruct"
    NVIDIA_VISION_MODEL: str = "meta/llama-3.2-11b-vision-instruct"
    NVIDIA_FALLBACK_MODEL: str = "mistralai/mistral-7b-instruct-v0.3"
    LLM_TEMPERATURE: float = 0.3
    LLM_MAX_TOKENS: int = 2048
    LLM_TIMEOUT: int = 120
    
    # Processing
    MAX_PAGES_PER_REPORT: int = 20

    # Security and request controls
    AUTH_ENABLED: bool = False
    APP_API_TOKEN: Optional[str] = None
    JWT_SECRET_KEY: str = "change-this-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS: int = 60
    RATE_LIMIT_WINDOW_SECONDS: int = 60
    
    class Config:
        env_file = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
