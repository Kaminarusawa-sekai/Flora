# memory/resource.py
from typing import List, Dict
import chromadb
from chromadb.utils import embedding_functions
import os

class ResourceMemory:
    def __init__(self, path="./chroma_db"):
        self.client = chromadb.PersistentClient(path=path)
        self.collection = self.client.get_or_create_collection(
            name="resources",
            metadata={"hnsw:space": "cosine"}
        )
        # 使用 Qwen Embedding
        self.embedding_func = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"  # 可替换为 Qwen Embedding API
        )

    def add(self, content: str, metadata: Dict = None, doc_id: str = None):
        self.collection.add(
            documents=[content],
            metadatas=[metadata or {}],
            ids=[doc_id or f"doc_{hash(content) % 100000}"]
        )

    def search(self, query: str, n_results: int = 3) -> List[Dict]:
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results
        )
        return [
            {"content": doc, "score": score}
            for doc, score in zip(results['documents'][0], results['distances'][0])
        ] if results['documents'] else []