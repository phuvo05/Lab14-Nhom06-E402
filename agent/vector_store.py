import os
import math
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


class BM25Indexer:
    """BM25 ranker for keyword-based retrieval. Complement to vector search."""

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.doc_lengths: List[int] = []
        self.avgdl: float = 0.0
        self.doc_freqs: Dict[str, int] = {}
        self.idf: Dict[str, float] = {}
        self.doc_term_freqs: List[Dict[str, int]] = []
        self.vocab: List[str] = []

    def _tokenize(self, text: str) -> List[str]:
        return text.lower().split()

    def _build_index(self, documents: List[Document]) -> None:
        self.doc_term_freqs = []
        self.doc_lengths = []
        self.doc_freqs = {}

        for doc in documents:
            tokens = self._tokenize(doc.text)
            self.doc_lengths.append(len(tokens))
            tf_map = {}
            for token in tokens:
                tf_map[token] = tf_map.get(token, 0) + 1
            self.doc_term_freqs.append(tf_map)

            for token in set(tokens):
                self.doc_freqs[token] = self.doc_freqs.get(token, 0) + 1

        self.avgdl = sum(self.doc_lengths) / len(self.doc_lengths) if self.doc_lengths else 1
        self.vocab = list(self.doc_freqs.keys())

        n = len(documents)
        for token in self.vocab:
            df = self.doc_freqs[token]
            self.idf[token] = math.log((n - df + 0.5) / (df + 0.5) + 1)

    def add_documents(self, documents: List[Document]) -> None:
        self._build_index(documents)

    def search(self, query: str, top_k: int = 10) -> List[Tuple[int, float]]:
        """Return list of (doc_index, score) sorted by BM25 score."""
        if not self.doc_term_freqs:
            return []

        query_tokens = self._tokenize(query)
        scores = []

        for i, tf_map in enumerate(self.doc_term_freqs):
            score = 0.0
            for token in query_tokens:
                if token in tf_map:
                    tf = tf_map[token]
                    idf = self.idf.get(token, 0)
                    dl = self.doc_lengths[i]
                    numerator = tf * (self.k1 + 1)
                    denominator = tf + self.k1 * (1 - self.b + self.b * dl / self.avgdl)
                    score += idf * numerator / denominator
            scores.append(score)

        indexed_scores = list(enumerate(scores))
        indexed_scores.sort(key=lambda x: x[1], reverse=True)
        return indexed_scores[:top_k]


class CrossEncoderReranker:
    """Cross-Encoder for semantic reranking of retrieved candidates."""

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self.model_name = model_name
        self.model = None
        self._load_model()

    def _load_model(self):
        try:
            from sentence_transformers import CrossEncoder as STCrossEncoder
            self.model = STCrossEncoder(self.model_name)
        except ImportError:
            self.model = None

    def rerank(self, query: str, candidates: List[Document], top_k: int = 5) -> List[Tuple[Document, float]]:
        if not candidates or not self.model:
            return [(doc, 1.0 / (i + 1)) for i, doc in enumerate(candidates[:top_k])]

        try:
            pairs = [[query, doc.text] for doc in candidates]
            scores = self.model.predict(pairs)

            doc_scores = list(zip(candidates, scores))
            doc_scores.sort(key=lambda x: x[1], reverse=True)
            return doc_scores[:top_k]
        except Exception:
            return [(doc, 1.0 / (i + 1)) for i, doc in enumerate(candidates[:top_k])]


class VectorStore:
    def __init__(
        self,
        embedding_model: str = "openai",
        embed_batch_size: int = 32,
        use_bm25: bool = True,
        use_reranker: bool = True,
        alpha: float = 0.5,
    ):
        """
        Enhanced VectorStore with hybrid search (dense + BM25) and reranking.

        Args:
            embedding_model: "openai" or "fake"
            embed_batch_size: Batch size for embedding computation
            use_bm25: Enable BM25 keyword search (hybrid mode)
            use_reranker: Enable Cross-Encoder reranking
            alpha: Weight for dense search in hybrid scoring (1-alpha for BM25)
        """
        self.documents: List[Document] = []
        self.embeddings: Optional[np.ndarray] = None
        self.embedding_model = embedding_model
        self.embed_batch_size = embed_batch_size
        self._embedding_cache: Dict[str, np.ndarray] = {}
        self.use_bm25 = use_bm25
        self.use_reranker = use_reranker
        self.alpha = alpha

        self.bm25 = BM25Indexer()
        self.reranker = CrossEncoderReranker()

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

        n_before = len(self.documents)
        for i, doc in enumerate(documents):
            doc.embedding = embeddings[i]
            self.documents.append(doc)

        if n_before == 0:
            self.embeddings = embeddings
        else:
            self.embeddings = np.vstack([self.embeddings, embeddings])

        if self.use_bm25:
            self.bm25 = BM25Indexer()
            self.bm25.add_documents(self.documents)

        return [doc.id for doc in documents]

    def _dense_search(self, query: str, top_k: int = 20) -> List[Tuple[Document, float]]:
        if not self.documents or self.embeddings is None:
            return []

        query_emb = self._get_embedding(query)
        query_emb = query_emb / (np.linalg.norm(query_emb) + 1e-8)

        similarities = self.embeddings @ query_emb
        top_indices = np.argsort(similarities)[::-1][:top_k]

        results = []
        for idx in top_indices:
            if similarities[idx] > 0:
                results.append((self.documents[idx], float(similarities[idx])))
        return results

    def _bm25_search(self, query: str, top_k: int = 20) -> List[Tuple[int, float]]:
        return self.bm25.search(query, top_k)

    def search(self, query: str, top_k: int = 5) -> List[Document]:
        """
        Hybrid search: combine dense vector + BM25 keyword search,
        then rerank with Cross-Encoder for maximum quality.
        """
        if not self.documents:
            return []

        dense_results = self._dense_search(query, top_k=20)

        if self.use_bm25 and self.bm25.doc_term_freqs:
            bm25_results = self._bm25_search(query, top_k=20)

            bm25_scores = {idx: score for idx, score in bm25_results}
            bm25_max = max((s for s in bm25_scores.values()), default=1.0)

            dense_scores = {self.documents.index(doc): score for doc, score in dense_results}
            dense_max = max((s for s in dense_scores.values()), default=1.0)

            seen_indices = set(dense_scores.keys()) | set(bm25_scores.keys())
            hybrid_scores = {}
            for idx in seen_indices:
                d_score = (dense_scores.get(idx, 0) / dense_max) if dense_max > 0 else 0
                b_score = (bm25_scores.get(idx, 0) / bm25_max) if bm25_max > 0 else 0
                hybrid_scores[idx] = self.alpha * d_score + (1 - self.alpha) * b_score

            sorted_indices = sorted(hybrid_scores.keys(), key=lambda x: hybrid_scores[x], reverse=True)
            candidate_docs = [self.documents[idx] for idx in sorted_indices[:15]]
        else:
            candidate_docs = [doc for doc, _ in dense_results[:15]]

        if self.use_reranker and len(candidate_docs) > 1:
            reranked = self.reranker.rerank(query, candidate_docs, top_k=top_k)
            return [doc for doc, _ in reranked]

        return candidate_docs[:top_k]

    def search_v1_style(self, query: str, top_k: int = 5) -> List[Document]:
        """Pure dense vector search without BM25/reranking - for V1 baseline."""
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
    vs = VectorStore(use_bm25=True, use_reranker=True, alpha=0.5)
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
