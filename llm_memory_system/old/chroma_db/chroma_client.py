# chroma_db/chroma_client.py
import chromadb
from chromadb.config import Settings
import os

CHROMA_DIR = "chroma_storage"
os.makedirs(CHROMA_DIR, exist_ok=True)

client = chromadb.PersistentClient(path=CHROMA_DIR)

def get_or_create_collection(name: str):
    return client.get_or_create_collection(name=name)

def add_semantic_fact(collection_name: str, fact_id: str, text: str):
    collection = get_or_create_collection(collection_name)
    collection.add(documents=[text], ids=[fact_id])

def search_semantic(collection_name: str, query_text: str, n_results: int = 3):
    collection = get_or_create_collection(collection_name)
    results = collection.query(query_texts=[query_text], n_results=n_results)
    return list(zip(results["ids"][0], results["documents"][0])) if results["documents"] else []



