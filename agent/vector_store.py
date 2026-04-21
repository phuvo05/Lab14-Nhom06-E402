import os
import uuid
import hashlib
from typing import List, Dict, Tuple, Optional
import numpy as np

os.environ["TOKENIZERS_PARALLELISM"] = "false"

class Document:
    def __init__(self, text: str, doc_id: Optional[str] = None, metadata: Optional[Dict] = None):
        self.id = doc_id or hashlib.md5(text.encode()).hexdigest()[:12]
        self.text = text
        self.metadata = metadata or {}
        self.embedding: Optional[np.ndarray] = None

    def __repr__(self):
        return f"Document(id={self.id}, text={self.text[:50]}...)"


class VectorStore:
    def __init__(self, embedding_model: str = "openai", embed_batch_size: int = 32):
        self.documents: List[Document] = []
        self.embeddings: Optional[np.ndarray] = None
        self.embedding_model = embedding_model
        self.embed_batch_size = embed_batch_size
        self._embedding_cache: Dict[str, np.ndarray] = {}

    def _get_embedding(self, text: str) -> np.ndarray:
        if text in self._embedding_cache:
            return self._embedding_cache[text]

        try:
            from openai import OpenAI
            client = OpenAI()
            response = client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            embedding = np.array(response.data[0].embedding, dtype=np.float32)
        except Exception:
            embedding = self._fake_embedding(text)

        self._embedding_cache[text] = embedding
        return embedding

    def _fake_embedding(self, text: str) -> np.ndarray:
        vec = np.zeros(1536, dtype=np.float32)
        for i, char in enumerate(text):
            vec[i % 1536] += ord(char)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec

    def _compute_embeddings(self, texts: List[str]) -> np.ndarray:
        if self.embedding_model == "openai":
            try:
                from openai import OpenAI
                client = OpenAI()
                response = client.embeddings.create(
                    model="text-embedding-3-small",
                    input=texts
                )
                return np.array([item.embedding for item in response.data], dtype=np.float32)
            except Exception:
                pass

        return np.array([self._fake_embedding(t) for t in texts], dtype=np.float32)

    def add_documents(self, documents: List[Document]) -> List[str]:
        texts = [doc.text for doc in documents]
        embeddings = self._compute_embeddings(texts)

        for i, doc in enumerate(documents):
            doc.embedding = embeddings[i]
            self.documents.append(doc)

        if self.embeddings is None:
            self.embeddings = embeddings
        else:
            self.embeddings = np.vstack([self.embeddings, embeddings])

        return [doc.id for doc in documents]

    def search(self, query: str, top_k: int = 5) -> List[Document]:
        if not self.documents or self.embeddings is None:
            return []

        query_emb = self._get_embedding(query)
        query_emb = query_emb / (np.linalg.norm(query_emb) + 1e-8)

        similarities = self.embeddings @ query_emb
        top_indices = np.argsort(similarities)[::-1][:top_k]

        return [self.documents[i] for i in top_indices]

    def get_retriever(self):
        return self

    def get_document_by_id(self, doc_id: str) -> Optional[Document]:
        for doc in self.documents:
            if doc.id == doc_id:
                return doc
        return None

    def __len__(self):
        return len(self.documents)


def build_vector_store_from_dataset(dataset: List[Dict]) -> VectorStore:
    vs = VectorStore()
    docs = []
    seen_contexts = set()
    doc_id_map = {}

    for item in dataset:
        context = item.get("context", "")
        expected_ids = item.get("expected_retrieval_ids", [])

        if context and context not in seen_contexts:
            seen_contexts.add(context)
            meta = item.get("metadata", {})

            if expected_ids and expected_ids[0] not in doc_id_map:
                doc_id = expected_ids[0]
            else:
                doc_id = f"doc_{len(docs)}"

            doc_id_map[doc_id] = True
            doc = Document(
                text=context,
                doc_id=doc_id,
                metadata={
                    "source": meta.get("category", "unknown"),
                    "difficulty": meta.get("difficulty", "unknown"),
                    "type": meta.get("type", "unknown"),
                }
            )
            docs.append(doc)

    if docs:
        vs.add_documents(docs)

    return vs
