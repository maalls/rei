from datetime import date
import time
import json
from typing import Literal
from pydantic import BaseModel, Field
from src.langgraph.nodes.chat_node import ChatNode
from src.langgraph.nodes.chikichiki_node import ChikiChikiNode
from src.langgraph.nodes.should_reply_node import ShouldReplyNode
from src.langgraph.nodes.is_handover_reply import IsHandoverReplyNode
from src.langgraph.nodes.rag_node import RagNode
from src.langgraph.nodes.classify_intent_node import ClassifyIntentNode
from src.langgraph.nodes.handover_node import HandoverNode
from src.langgraph.state import State
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver

from langchain_openai import ChatOpenAI
from src.langgraph.nomic_vector_store import NomicVectorStore
from src.telegram_bot.admin_bot import AdminBot


class RewrittenQuery(BaseModel):
    question: str
    reason: str

class Response(BaseModel):
    content: str | None
    


class LangGraphApp:
    def __init__(self, 
                 llm: ChatOpenAI, 
                 vector_store: NomicVectorStore,
                 admin_bot: AdminBot
                 
                 ):
        self.llm = llm
        self.vector_store = vector_store
        self.admin_bot = admin_bot

        def rewrite_knowledge_query(state: State):
            structured_llm = llm.with_structured_output(RewrittenQuery)

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

            
    

        

        graph = StateGraph(State)

        chat_node = ChatNode(llm=llm, admin_username=self.admin_bot.username)
        chiki_chiki_node = ChikiChikiNode(llm=llm)
        should_reply_node = ShouldReplyNode(llm=llm, admin_username=self.admin_bot.username)
        handover_node = HandoverNode(llm=llm, admin_bot=self.admin_bot)
        is_handover_reply_node = IsHandoverReplyNode(llm=llm, admin_bot=self.admin_bot, vector_store=self.vector_store, forward_content=self.forward_content)
        classify_intent_node = ClassifyIntentNode(llm=llm)
        rag_node = RagNode(llm=llm, vector_store=self.vector_store)
        graph.add_node("chikichiki", chiki_chiki_node.run)
        graph.add_node("should_reply", should_reply_node.run)
        graph.add_node("is_handover_reply", is_handover_reply_node.run)
        graph.add_node("classify_intent", classify_intent_node.run)
        graph.add_node("chat_agent", chat_node.run)
        graph.add_node("rag_query", rewrite_knowledge_query)
        graph.add_node("rag_agent", rag_node.run)
        graph.add_node("handover_request", handover_node.run)
        graph.add_edge(START, "chikichiki")
        graph.add_conditional_edges(
            "chikichiki", lambda state: state["is_chikichiki"], {
                True: END,
                False: "is_handover_reply"
            }
        )
        graph.add_conditional_edges(
            "is_handover_reply", lambda state: state.get("message_intent") == "request_reply", {
                True: END,
                False: "should_reply"
            }
        )
        graph.add_conditional_edges(
            "should_reply",
            lambda state: state["should_reply"],
            {
                True: "classify_intent",
                False: END,
            }
        )
        graph.add_conditional_edges("classify_intent", lambda state: state["message_intent"], {
            "chat": "chat_agent",
            "knowledge": "rag_query",
            "handover_request": "handover_request",
            "request_reply": END,
            "chikichiki": "chikichiki"
        })
        graph.add_edge("chat_agent", END)
        graph.add_edge("rag_query", "rag_agent")
        graph.add_edge("rag_agent", END)
        graph.add_edge("handover_request", END)
        graph.add_edge("chikichiki", END)

        checkpointer = InMemorySaver()
        self.app = graph.compile(checkpointer=checkpointer)

    async def invoke(self, message):

        config = {
            'configurable': {
                'thread_id': str(message["chat_id"]),
            }
        }
        state = await self.app.ainvoke({
            "messages": [{"role": "user", "content": json.dumps(message)}]
        }, config=config)
        if state["should_reply"]:
            return json.loads(state['messages'][-1].content)["text"].strip()
        else:
            return False
        
    async def forward_content(self, thread_id, forwarded_content):
        await self.app.aupdate_state(
        config={
            "configurable": {
                "thread_id": str(thread_id),
            }
        },
        values={
            "messages": [
                {
                    "role": "assistant",
                    "content": json.dumps(forwarded_content, ensure_ascii=False),
                }
            ]
        },
    )
    


    