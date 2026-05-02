from fastapi import APIRouter, status

from app.config import get_settings

router = APIRouter()
settings = get_settings()

@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    return {
        "status": "ok",
        "version": settings.APP_VERSION,
        "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
    }


@router.get("/health/models", status_code=status.HTTP_200_OK)
async def health_models():
    from app.core.nlp_engine import NLPEngine
    from app.core.rag_engine import RAGEngine

    nlp = NLPEngine()
    rag = RAGEngine()
    return {
        "nlp": {
            "backend": nlp.backend,
            "active_model": nlp.active_model,
        },
        "rag": {
            "embedding_backend": rag.embedding_backend,
            "embedding_model": settings.EMBEDDING_MODEL,
            "embedding_model_path": settings.EMBEDDING_MODEL_PATH,
            "chunks_loaded": len(rag.id_to_chunk),
            "index_available": rag.index is not None,
        },
    }
