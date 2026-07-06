from langchain_core.vectorstores import InMemoryVectorStore
from langchain_core.embeddings import Embeddings
from langchain_openai import OpenAIEmbeddings


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
    def __init__(self, model, base_url, api_key):
        super().__init__(embedding=NomicEmbeddings(model=model, base_url=base_url, api_key=api_key))

        