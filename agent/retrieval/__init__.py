"""Retrieval module — embeddings, vector store, and chunking.

This package provides the building blocks for retrieval-augmented generation
(RAG) workflows:

    - *embeddings*   : Embedding provider with an automatic fallback chain
                       (Ollama → OpenAI → HuggingFace).
    - *chunker*      : Splits markdown documents into overlapping text chunks
                       suitable for embedding.
    - *vector_store* : ChromaDB wrapper with lazy initialisation and cache-
                       aware auto-rebuild when source documents change.
"""
