from app.services.knowledge_base import KnowledgeBaseBuilder


def main():
    builder = KnowledgeBaseBuilder()
    chunks = builder.build_chunks_from_sources()
    print(f"Built {len(chunks)} knowledge base chunks.")


if __name__ == "__main__":
    main()
