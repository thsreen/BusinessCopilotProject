"""Document chunking utilities for RAG."""
import os
import re


def chunk_text(text: str, source: str, chunk_size: int = 500, overlap: int = 50) -> list[dict]:
    """Split a document into overlapping chunks."""
    paragraphs = re.split(r'\n\s*\n', text)
    chunks = []
    current_chunk = ""
    current_size = 0

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        para_words = len(para.split())

        if current_size + para_words > chunk_size and current_chunk:
            chunks.append({
                "content": current_chunk.strip(),
                "source": source,
                "chunk_id": len(chunks),
            })
            # Overlap: keep last few sentences
            sentences = current_chunk.split(". ")
            overlap_text = ". ".join(sentences[-3:]) if len(sentences) > 3 else current_chunk
            current_chunk = overlap_text + ". " + para
            current_size = len(current_chunk.split())
        else:
            if current_chunk:
                current_chunk += "\n\n" + para
            else:
                current_chunk = para
            current_size += para_words

    if current_chunk.strip():
        chunks.append({
            "content": current_chunk.strip(),
            "source": source,
            "chunk_id": len(chunks),
        })

    return chunks


def chunk_all_docs(data_dir: str) -> list[dict]:
    """Chunk all markdown documents in the data/docs directory."""
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
