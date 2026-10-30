"""Answer questions about a document using only its own text."""
import hashlib
import os

from backend import config, llm

ANSWER_PROMPT = (
    "You answer questions about a document. Use only the provided context. "
    "If the answer is not in the context, say you couldn't find it in the document."
)

_embeddings = None


def _get_embeddings():
    # Heavy imports and model loading take seconds, so do them once, on first use
    global _embeddings
    if _embeddings is None:
        import torch
        from langchain_huggingface import HuggingFaceEmbeddings

        _embeddings = HuggingFaceEmbeddings(
            model_name=config.EMBED_MODEL,
            model_kwargs={"device": "cuda" if torch.cuda.is_available() else "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
    return _embeddings


def split(text):
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter(chunk_size=config.SEARCH_CHUNK_CHARS, chunk_overlap=config.SEARCH_CHUNK_OVERLAP)
    return splitter.split_text(text)


def _load_or_build_index(text, index_dir, log):
    from langchain_community.vectorstores import FAISS

    embeddings = _get_embeddings()

    # The index is reused only if it was built from exactly this text with this embedding model
    digest = hashlib.sha256(f"{config.EMBED_MODEL}\n{text}".encode("utf-8")).hexdigest()
    digest_file = os.path.join(index_dir, "source.sha256")

    if os.path.exists(digest_file):
        with open(digest_file, encoding="utf-8") as f:
            if f.read().strip() == digest:
                log("[✔] Loaded saved search index.")
                # Safe: this index was written by this program, not downloaded
                return FAISS.load_local(index_dir, embeddings, allow_dangerous_deserialization=True)

    log("[🔄] Building search index...")
    db = FAISS.from_texts(split(text), embeddings)
    db.save_local(index_dir)
    with open(digest_file, "w", encoding="utf-8") as f:
        f.write(digest)
    return db


class DocumentRAG:
    def __init__(self, text, index_dir, log=print):
        from langchain_community.retrievers import BM25Retriever

        # Vector search understands meaning; BM25 catches exact terms like names, codes, and numbers
        self.vector_retriever = _load_or_build_index(text, index_dir, log).as_retriever(search_kwargs={"k": config.TOP_K})
        self.keyword_retriever = BM25Retriever.from_texts(split(text))
        self.keyword_retriever.k = config.TOP_K

    def retrieve(self, question):
        # Reciprocal rank fusion: passages ranked high by either search come first
        scores = {}
        for retriever in (self.vector_retriever, self.keyword_retriever):
            for rank, doc in enumerate(retriever.invoke(question)):
                scores[doc.page_content] = scores.get(doc.page_content, 0) + 1 / (60 + rank)
        return sorted(scores, key=scores.get, reverse=True)[:config.TOP_K + 2]

    def answer_stream(self, question, sources):
        context = "\n\n---\n\n".join(sources)
        return llm.chat(
            [
                {"role": "system", "content": ANSWER_PROMPT},
                {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"},
            ],
            stream=True,
        )

    def ask(self, question):
        return "".join(self.answer_stream(question, self.retrieve(question)))
