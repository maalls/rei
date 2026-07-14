
from pydantic import BaseModel, Field
from typing import Literal
from src.langgraph.state import State
from src.langgraph.format_response import format_response
from langchain_core.messages import SystemMessage
import json
class CouldReplyClassifier(BaseModel):
    could_reply: Literal['yes', 'no'] = Field(..., description="Classify whether the LLM could find the information to the user requested or not.")

class RewrittenQuery(BaseModel):
    question: str
    reason: str

class RagNode:
    def __init__(self, llm, vector_store, admin_username: str):
        self.llm = llm
        self.vector_store = vector_store
        self.admin_username = admin_username

    async def run(self, state: State):

        rewritten_query = self.rewrite_knowledge_query(state)
        query = rewritten_query["rag_query"]
        print("[prompting rag] query:", query)
        docs = self.vector_store.similarity_search(query, k=5)
        print("[prompt_llm_rag] docs: (", len(self.vector_store.store), " total docs)")

        for doc in docs:
            print("[prompt_llm_rag] doc ", doc.page_content) 
        context = "\n".join([doc.page_content for doc in docs])
        messages = [SystemMessage(content=f"You are a helpful assistant. You are a knowledge agent. You have access to the following knowledge:\n{context}\nAnswer the user question based on the knowledge provided and the chat history. if you don't have the answer, say 'I don't know'. Your response must be in plain text with only your reply. Answer in the same language as the user question.")] + state["messages"]
        response = self.llm.invoke(messages)            
        response.content = self.normalize_text(response.content)
        print("[prompt_llm_rag] response:", response.content)

        structured_llm = self.llm.with_structured_output(CouldReplyClassifier)
        message = format_response(state["messages"], response, self.admin_username)

        result = structured_llm.invoke([
            {'role': 'system', 'content': 'Determine whether the you could answer to the user question (yes) or if you could not retrieve the answer from the knowledge base (no).'},
        ] + state["messages"] + [message])
        print("[classify_rag_response] result:", result.could_reply)

        if(result.could_reply == 'yes'):
            print("[prompt_llm_rag] rag could replied: ", result.could_reply)
            reply = {"messages": [format_response(messages, response, self.admin_username)]}
        else:
            messages =  [state['messages'][-1]] + [{
                "role": "user",
                "content": "Translate in the same language as the previous messages (do not use quote or any formatting):\n " + "'I couldn't find the information, would you like me to transmit the request to my admin?'"
            }] 
            print("[prompt_llm_rag] couldn't find the answer in the knowledge base.")
            response = self.llm.invoke(messages)
            print('[prompt_llm_rag] response: ', response.content)
            reply =  {"messages": [format_response(state["messages"], response, self.admin_username)]}
    
        return {**reply, **rewritten_query}
    
    def normalize_text(self, value: str) -> str:
        try:
            data = json.loads(value)
            if isinstance(data, dict) and "text" in data:
                return data["text"]
        except json.JSONDecodeError:
            pass

        return value
    
    def rewrite_knowledge_query(self, state: State):
            structured_llm = self.llm.with_structured_output(RewrittenQuery)

            log = "\n".join(
                m.content for m in state["messages"][-6:]
            )
            prompt = f"""
                Tu reformules le DERNIER message utilisateur en une requête autonome pour un RAG.

                Règles:
                - Résous les pronoms et références implicites avec l'historique.
                - "sa", "son", "lui", "il", "elle" doivent être remplacés par la personne concernée.
                - Ne réponds pas à la question.
                - Retourne une requête complète, claire et autonome.

                Historique des messages récents (du plus ancien au plus récent):
                {log}
                """
            print("[rewrite_knowledge_query] prompt:", prompt)
            result = structured_llm.invoke([
                {
                    "role": "system",
                    "content": prompt
                }
            ])

            print("[rewrite_knowledge_query] rag question: ", result.question)

            return {
                "rag_query": result.question,
                "rag_query_reason": result.reason,
            }    