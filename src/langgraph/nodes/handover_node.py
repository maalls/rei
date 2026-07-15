
import json
from pydantic import BaseModel, Field
from typing import Literal
from src.langgraph.state import State
from src.langgraph.response import Response
from src.langgraph.format_response import format_response
from langchain_core.messages import SystemMessage

from src.telegram_bot.admin_bot import AdminBot
class HumanRequest(BaseModel):
    action: Literal["handover_request"]
    message: str = Field(..., description="The requested message to hand over")


class HandoverNode:

    def __init__(self, llm, admin_bot: AdminBot):
        self.llm = llm
        self.admin_bot = admin_bot

    async def run(self, state: State):
        print("[handover_request] start") 
        content = json.loads(state["messages"][-1].content)
        chat_id = content["chat_id"]
        message_id = content["message_id"]

        rewritten_query = state["rag_query"]
        if not rewritten_query:
            print("[handover_request] no rag query found, using last message text")
            llm_structured = self.llm.with_structured_output(HumanRequest)

            historic = []
            content = json.loads(state["messages"][-1].content)
            chat_id = content["chat_id"]
            
            for message in state["messages"][-10:]:
                historic.append(self.to_llm_message(message=message))

            print("[handover_request] historic", json.dumps(historic))

            system_prompt = SystemMessage(
                content="""
                
            You are in charge of handing over a specific request.
            Your role is to formulate a clear and concise request that the human administrator can understand and act upon.
            Past request that has been already answered by the assistant should not be included in the request.
            Extract ONLY the information that the human needs to answer.

            Rules:
            - Keep the original meaning.
            - Do not answer the request.
            - Do not mention the AI assistant.
            - Remove conversational filler.
            - Rewrite as a direct question or request.
            - Preserve all important details.
            - Do not include questions that have already been answered by the assistant.
            - If the request is ambiguous, include enough context to remove the ambiguity.
            """
            )
            response = await llm_structured.ainvoke(
                [system_prompt] + historic
            )
        else:
            print("[handover_request]  request", rewritten_query)  # "ex: Quel est l' email de Malo?"
            await self.admin_bot.request_admin(from_channel_id=chat_id, from_message_id=message_id, text=rewritten_query)
            response = Response(content= f"La demande {rewritten_query} a bien été transmise. Je vous tiendrai informé dès que j'aurai une réponse.")
        return { "messages": format_response(state["messages"], response, self.admin_bot.username) }
     
    
    def to_llm_message(self, message):
        data = json.loads(message.content)
        username = data.get("from", {}).get("username", "unknown")
        role = "assistant" if username == "@" + self.admin_bot.username else "user"
        text = data.get("text", "")
        text = text.replace("@" + self.admin_bot.username, "").strip()
        return {
            "role": role,
            "content": text
        }
