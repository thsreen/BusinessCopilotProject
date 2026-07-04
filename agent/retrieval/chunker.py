"""Document chunking utilities for RAG.

Splits markdown documents into smaller, overlapping text chunks that fit
within the context window of embedding models. Each chunk is annotated with
its source filename and a sequential chunk ID for downstream traceability.

Two chunking strategies are provided:
    1. *chunk_text*      — splits a single text into chunks by paragraph
                           boundaries, with configurable token budget and
                           overlap.
    2. *chunk_all_docs*  — convenience wrapper that iterates over all ``.md``
                           files in a given directory and chunks them.
"""
import os
import re


def chunk_text(
    text: str, source: str, chunk_size: int = 500, overlap: int = 50
) -> list[dict]:
    """Split a document into overlapping chunks at paragraph boundaries.

    Paragraphs (text separated by one or more blank lines) are accumulated
    until the word count exceeds *chunk_size*. Before starting a new chunk,
    the last few sentences of the current chunk are prepended to produce
    overlap, preserving cross-paragraph context.

    Args:
        text:       The raw document text to chunk.
        source:     An identifier for the source document (e.g. filename).
                    Included in every output chunk as the ``"source"`` field.
        chunk_size: Target chunk size in **words** (not tokens). 500 words
                    is a rough approximation of 500 tokens for English text.
                    Defaults to 500.
        overlap:    The number of **words** of overlap between consecutive
                    chunks. This is approximated by keeping the last ~3
                    sentences of the previous chunk. Defaults to 50.

    Returns:
        A list of chunk dictionaries, each containing:
            - ``content``  : The chunk text.
            - ``source``   : The original *source* parameter.
            - ``chunk_id`` : Zero-based index in the order chunks were created.

    Notes:
        - Paragraphs longer than *chunk_size* are not further subdivided; they
          are placed in the chunk where they fit or start a new chunk.
        - The overlap mechanism uses sentence boundaries (``. ``) for a
          natural break, not exact word counts. This means the actual overlap
          may be slightly larger or smaller than *overlap*.
    """
    # Split on one or more blank lines to get paragraph-level units
    paragraphs = re.split(r"\n\s*\n", text)
    chunks = []
    current_chunk = ""
    current_size = 0

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        para_words = len(para.split())

        # If adding this paragraph would exceed the budget *and* we already
        # have content, finalise the current chunk and start a new one.
        if current_size + para_words > chunk_size and current_chunk:
            chunks.append(
                {
                    "content": current_chunk.strip(),
                    "source": source,
                    "chunk_id": len(chunks),
                }
            )
            # Overlap: keep the last ~3 sentences of the finished chunk so
            # the next chunk has context for cross-paragraph references.
            sentences = current_chunk.split(". ")
            overlap_text = (
                ". ".join(sentences[-3:]) if len(sentences) > 3 else current_chunk
            )
            current_chunk = overlap_text + ". " + para
            current_size = len(current_chunk.split())
        else:
            if current_chunk:
                current_chunk += "\n\n" + para
            else:
                current_chunk = para
            current_size += para_words

    # Don't forget the last in-progress chunk
    if current_chunk.strip():
        chunks.append(
            {
                "content": current_chunk.strip(),
                "source": source,
                "chunk_id": len(chunks),
            }
        )

    return chunks


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
        return all_chunks  # Nothing to do — return early, no error

    for fname in os.listdir(docs_dir):
        if fname.endswith(".md"):
            fpath = os.path.join(docs_dir, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                text = f.read()
            chunks = chunk_text(text, source=fname)
            all_chunks.extend(chunks)

    return all_chunks
