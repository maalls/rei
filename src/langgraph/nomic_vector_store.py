from langchain_core.vectorstores import InMemoryVectorStore
from langchain_core.embeddings import Embeddings
from langchain_openai import OpenAIEmbeddings
import os

class NomicEmbeddings(Embeddings):

    def __init__(self, model, base_url, api_key):
        self.client = OpenAIEmbeddings(
            model=model,
            base_url=base_url,
            api_key=api_key,
            check_embedding_ctx_length=False
        )

    def embed_query(self, text: str) -> list[float]:
        return self.client.embed_query(f"search_query: {text}")

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [
            self.client.embed_query(f"search_document: {text}")
            for text in texts
        ]
    
    

class NomicVectorStore(InMemoryVectorStore):
    def __init__(self, model, base_url, api_key, storage_file: str | None = None):
        super().__init__(embedding=NomicEmbeddings(model=model, base_url=base_url, api_key=api_key))
        self.storage_file = storage_file

    def add_new_text(self, text: str):
        print("[NomicVectorStore][add_new_text] Adding new text to vector store and saving to storage file:", text)
        super().add_texts([text])
        if self.storage_file:
            with open(self.storage_file, "a") as f:
                print("[NomicVectorStore][add_new_text] Appending new text to storage file:", self.storage_file)
                f.write(text + "\n")
    def load(self):
        if self.storage_file and os.path.exists(self.storage_file):
            with open(self.storage_file, "r") as f:
                texts = [line.strip() for line in f if line.strip()]
                if texts:
                    self.add_texts(texts)
                    print(f"[NomicVectorStore][load] Loaded {len(texts)} texts from storage file {self.storage_file}.")
        else:
            print(f"Storage file {self.storage_file} does not exist. Starting with an empty vector store.")
            # create the directory if it doesn't exist
            if self.storage_file:
                os.makedirs(os.path.dirname(self.storage_file), exist_ok=True)
                with open(self.storage_file, "w") as f:
                    pass  # create an empty file  
            else:
                raise ValueError("Storage file path is not provided. Cannot create storage file.")
    
        