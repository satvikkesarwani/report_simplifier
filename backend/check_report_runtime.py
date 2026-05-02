from app.core.nlp_engine import NLPEngine
from app.core.rag_engine import RAGEngine


def main() -> None:
    nlp = NLPEngine()
    rag = RAGEngine()
    print(
        {
            "nlp_backend": nlp.backend,
            "nlp_model": nlp.active_model,
            "embedding_backend": rag.embedding_backend,
            "chunks_loaded": len(rag.id_to_chunk),
            "index_available": rag.index is not None,
        }
    )


if __name__ == "__main__":
    main()
