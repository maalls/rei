
from src.langgraph.classifier.could_reply_classifier import CouldReplyClassifier
from src.langgraph.state import State
from src.langgraph.response import Response
from src.langgraph.format_response import format_response
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage
import json
import time
from datetime import date

from src.telegram_bot.admin_bot import AdminBot

class IsHandoverReplyNode:
    def __init__(self, llm, admin_bot: AdminBot, vector_store, forward_content):
        self.llm = llm
        self.admin_bot = admin_bot
        self.vector_store = vector_store
        self.forward_content = forward_content
        self.could_reply_classifier = CouldReplyClassifier(llm)

    async def run(self, state: State):
        request_reply = await self.is_request_reply(state)
        if request_reply:
            message = format_response(state["messages"], request_reply, "@" + self.admin_bot.username)
            return {"message_intent": "request_reply", "messages": [message], "should_reply": True}

    async def is_request_reply(self, state: State):

        message = state["messages"][-1]
        content = json.loads(message.content)
        if(content.get("reply_to")):
            message_id = content["reply_to"]["message_id"]
            pending_request = self.admin_bot.find_pending_request(message_id=message_id)
            if pending_request:
                print("[is_request_reply] pending request found", pending_request["reply_to_channel_id"], content["text"])
                text = self.format_request_reply(request=pending_request["request"], reply=content["text"])
                await self.admin_bot.send_message(chat_id=pending_request["reply_to_channel_id"], reply_to_message_id=pending_request["from_message_id"], text=text)

                forwarded_content = {
                    "chat_id": pending_request["reply_to_channel_id"],
                    "text": "The answer: " + text + " a été envoyé à l'utilisateur.",
                    "from": {
                        "username": "@" + self.admin_bot.username,
                    },
                    "date": date.today().isoformat(),
                    "timestamp": int(time.time()),
                }
                await self.forward_content(pending_request["reply_to_channel_id"], forwarded_content)
                self.admin_bot.remove_pending_request(message_id=message_id)
                
                could_reply = self.could_reply_classifier.classify(pending_request["request"], content["text"]) 
                if could_reply:
                    print("[is_request_reply] the admin could reply to the user request, storing new knowledge.")
                    self.store_new_knowledge(text=text)
                else:
                    print("[is_request_reply] the admin could not reply to the user request, not storing new knowledge.")
                return Response(content=text)
            else:
                return False
        else:
            return False
        
    
    def format_request_reply(self, request: str, reply: str) -> str:

        class RequestReply(BaseModel):
            formatted_reply: str = Field(..., description="Format the question and answer so that it can be sent to the user who made the initial request and also stored in the knowledge base. The question and answer must be clearly identified.")
        
        prompt = SystemMessage(content=f"""
            Formattes la question et la reponse afin qu'elle puisse etre envoyee a l'utilisateur qui a fait la demande initiale ainsi que d'etre stocker dans la base de connaissances. La question et la reponse doivent etre clairement identifiees:
            Question: {request}
            Réponse: {reply}

            Exemple de formatage (1):
            input:
            Question: Quelle est la couleur préférée de Malo Yamakado?
            Réponse: bleu.
            output: 
            La couleur préférée de Malo Yamakado est bleu.

            Exemple de formatage (2):
            input:
            Question: Quelle est la date de naissance de Malo Yamakado?
            Réponse: 12 janvier 1990.
            output: 
            La date de naissance de Malo Yamakado est le 12 janvier 1990.

            Dans les examples ci dessus, ta reponse doit correspondre au format attendu.
            """
        )
        llm = self.llm.with_structured_output(RequestReply)
        result = llm.invoke([prompt])
        print("[format_request_reply] request:", request, "reply:", reply, "result:", result.formatted_reply)
        return result.formatted_reply
    

    def store_new_knowledge(self, text: str):
        print("[store_new_knowledge] storing new knowledge:", text)
        self.vector_store.add_new_text(text)