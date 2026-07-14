"""Document chunking utilities for RAG.

Splits markdown documents into smaller, overlapping text chunks that fit
within the context window of embedding models. Each chunk is annotated with
its source filename and a sequential chunk ID for downstream traceability.

Uses LangChain's ``RecursiveCharacterTextSplitter`` under the hood, which splits on
paragraph, sentence, and word boundaries in that order of priority.
"""
import os

from langchain_text_splitters import RecursiveCharacterTextSplitter


def chunk_text(
    text: str, source: str, chunk_size: int = 500, overlap: int = 50
) -> list[dict]:
    """Split a document into overlapping chunks using RecursiveTextSplitter.

    Delegates to LangChain's ``RecursiveCharacterTextSplitter`` with default
    separators (``\\n\\n``, ``\\n``, ``.``, `` ``) so that paragraphs are
    preserved where possible, falling back to sentence and word boundaries
    when a single paragraph exceeds *chunk_size*.

    Args:
        text:       The raw document text to chunk.
        source:     An identifier for the source document (e.g. filename).
                    Included in every output chunk as the ``"source"`` field.
        chunk_size: Target chunk size in **characters** (RecursiveTextSplitter
                    default unit). 500 characters is a rough approximation of
                    120-150 tokens for English text. Defaults to 500.
        overlap:    Number of characters of overlap between consecutive chunks.
                    Defaults to 50.

    Returns:
        A list of chunk dictionaries, each containing:
            - ``content``  : The chunk text.
            - ``source``   : The original *source* parameter.
            - ``chunk_id`` : Zero-based index in the order chunks were created.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=overlap,
        length_function=len,
        separators=["\n\n", "\n", ".", " "],
    )
    docs = splitter.create_documents([text])
    return [
        {
            "content": doc.page_content,
            "source": source,
            "chunk_id": i,
        }
        for i, doc in enumerate(docs)
    ]


def chunk_all_docs(data_dir: str) -> list[dict]:
    """Chunk all markdown documents found in ``<data_dir>/docs/``.

    Args:
        data_dir: Path to the project's data directory. The subdirectory
                  ``docs/`` will be scanned for ``.md`` files.

    Returns:
        A flat list of chunk dictionaries (as produced by *chunk_text*),
        ordered by the order files are listed from the filesystem.

    Notes:
        - Non-existent or empty ``docs/`` directories cause a silent early
          return with an empty list.
        - Each file is read with UTF-8 encoding.
    """
    docs_dir = os.path.join(data_dir, "docs")
    all_chunks = []

    if not os.path.exists(docs_dir):
        return all_chunks

    for fname in os.listdir(docs_dir):
        if fname.endswith(".md"):
            fpath = os.path.join(docs_dir, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                text = f.read()
            chunks = chunk_text(text, source=fname)
            all_chunks.extend(chunks)

    return all_chunks
