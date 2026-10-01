
from pydantic import BaseModel
from src.langgraph.classifier.could_reply_classifier import CouldReplyClassifier
from src.langgraph.state import State
from src.langgraph.format_response import format_response
from langchain_core.messages import SystemMessage
import json
from src.langgraph.response import Response
from src.telegram_bot.admin_bot import AdminBot

class RewrittenQuery(BaseModel):
    question: str
    reason: str
    identity_response: str | None = None

class RagNode:
    def __init__(self, llm, vector_store, admin_bot: AdminBot):
        self.llm = llm
        self.vector_store = vector_store
        self.admin_bot = admin_bot
        self.bot_username = self.admin_bot.username
        self.could_reply_classifier = CouldReplyClassifier(llm)


    async def run(self, state: State):
        rewritten_query = self.rewrite_knowledge_query(state)
        identity_response = rewritten_query.pop("identity_response")
        if identity_response:
            response = Response(content=identity_response)
            return {
                "messages": [format_response(state["messages"], response, self.bot_username)]
            }

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

        message = format_response(state["messages"], response, self.bot_username)

        could_reply = self.could_reply_classifier.classify(query, message)
        print("[classify_rag_response] result:", could_reply)
             
        if(could_reply):
            print("[prompt_llm_rag] rag could replied")
            reply = {"messages": [format_response(messages, response, self.bot_username)]}
        else:

            admin_info =self.admin_bot.get_admin_info()

            if admin_info:
                messages =  [state['messages'][-1]] + [{
                    "role": "user",
                    "content": "Translate in the same language as the previous messages (do not use quote or any formatting):\n " + f"'I couldn't find the information, would you like me to transmit the request to {admin_info['display_name']}?'"
                }] 
                print("[prompt_llm_rag] couldn't find the answer in the knowledge base.")
                response = self.llm.invoke(messages)
                print('[prompt_llm_rag] response: ', response.content)
                reply =  {"messages": [format_response(state["messages"], response, self.bot_username)]}
            else:
                print("[prompt_llm_rag] couldn't find the answer in the knowledge base and no admin is set.")
                response = Response(content="I couldn't find the information, and no admin is available to help.")
                reply = {"messages": [format_response(state["messages"], response, self.bot_username)]}

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

                                Exception pour les questions d'identité:
                                - Détecte leur sens dans n'importe quelle langue, sans te limiter à des formulations précises.
                                                                - La langue de réponse est celle du champ "text" du DERNIER message utilisateur. Ignore la
                                                                    langue des présentes consignes, des exemples et des anciens messages. Ne recopie pas en
                                                                    anglais les formulations anglaises ci-dessous si le dernier message est dans une autre langue.
                                                                - Si le dernier message signifie "Who are you?", remplis identity_response dans cette langue.
                                                                    Si l'expéditeur Telegram est @maalls, le sens est "I am you" (en français: "Je suis toi");
                                                                    sinon, le sens est "I am myself" (en français: "Je suis moi").
                                - Si le dernier message demande qui est Malo, et que l'expéditeur n'est pas @maalls, la réponse
                                  doit signifier "He is me" (en français: "Il est moi"), dans la langue du message.
                                - Pour les autres questions "Who is [name]?", remplis identity_response avec un compliment bref,
                                  positif, bienveillant et humoristique sur ce nom, dans la langue du message. Ne présente pas
                                  d'informations inventées comme des faits réels.
                                - Dans ces cas, identity_response contient uniquement le texte à envoyer. Pour les autres messages,
                                  identity_response doit être null et tu appliques les règles de reformulation ci-dessus.

                                Dernier message utilisateur (la langue de ce texte détermine la réponse):
                                {state["messages"][-1].content}

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
                "identity_response": result.identity_response,
            }    