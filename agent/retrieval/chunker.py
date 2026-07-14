
import os

from langchain_text_splitters import RecursiveCharacterTextSplitter

def chunk_text(
    text: str, source: str, chunk_size: int = 500, overlap: int = 50
) -> list[dict]:

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
