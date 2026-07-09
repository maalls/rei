import json
from typing import TypedDict, Annotated, Literal
from pydantic import BaseModel, Field

from typing import TypedDict
from langgraph.graph import MessagesState, StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph.message import add_messages
from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
from src.langgraph.nomic_vector_store import NomicVectorStore
from src.telegram_bot.admin_bot import AdminBot
class IntentClassifier(BaseModel):
    message_intent: Literal['chat', 'knowledge', 'coding', 'handover_request'] = Field(..., description="Classify whether the user want to just chat, ask for knowledge, change code in the project, or ask a human a question (handover_request).")
    description: str = Field("...", description="A detailed description of what the intent is based on the last message and the log history.")

class GroupIntent(BaseModel):
    reason: str = Field("...", description="An explanation on why the last message is addressed to this person")
    is_addressed_to: str = Field("...", description="The person in the chat likely to reply to the message.")
class RewrittenQuery(BaseModel):
    question: str
    reason: str

class Response(BaseModel):
    content: str | None
    
class State(TypedDict):
    messages: Annotated[list, add_messages]
    should_reply: str | None
    reason: str | None
    could_reply: str | None
    rag_query: str
    rag_query_reason: str

class CouldReplyClassifier(BaseModel):
    could_reply: Literal['yes', 'no'] = Field(..., description="Classify whether the LLM could find the information to the user requested or not.")


class HumanRequest(BaseModel):
    action: Literal["handover_request"]
    message: str = Field(..., description="The requested message to hand over")

class LangGraphApp:
    def __init__(self, 
                 llm: ChatOpenAI, 
                 vector_store: NomicVectorStore,
                 admin_bot: AdminBot
                 
                 ):
        self.llm = llm
        self.vector_store = vector_store
        self.admin_bot = admin_bot

        KNOWNLEDGES = [
            "Malo Yamakado email is dummy@gmail.com",
            "Malo Yamakado phone number is 650-996-1234",
            "Malo Yamakado address is 123 Main St, San Francisco, CA 94105",
            "Malo Yamakado favorite color is blue",
            "Malo Yamakado favorite food is sushi",
            "Jean Dupont favorite food is pizza",
            "Chang Lee favorite food is ramen",
        ]

        self.vector_store.add_texts(KNOWNLEDGES)

        def group_intent(state: State):
            print("group_intent", len(state["messages"]))

            last = json.loads(state["messages"][-1].content)
            last_text = last.get("text", "")                

            if(last["chat_type"] == "private"):
                print("it's a private chat so bot should reply")
                return {
                    "should_reply": True,
                    "reason": "it's a private chat so bot should reply"
                }

            if "@maalls_bot" in last_text.lower():
                print("@maalls_bot is mentioned in the message")
                return {
                    "should_reply": True,
                    "reason": "Le dernier message mentionne explicitement @maalls_bot.",
                }

            structured_llm = llm.with_structured_output(GroupIntent)

            logs = []
            for message in state["messages"]:
                message = json.loads(message.content)
                logs.append(f"from {message["from"]["username"]}: {message["text"]}")
            
            log = "\n".join(logs)
            print("log", log)
            result = structured_llm.invoke([
            SystemMessage(content=f"""
                Tu lis l'historique d'un groupe Telegram.

                Ton objectif est de déterminer à qui le DERNIER message est adressé.

                Règles prioritaires :
                1. Si le dernier message mentionne explicitement un username avec @, il est adressé à ce username.
                2. Si le dernier message commence par un prénom ou username suivi d'une virgule, il est adressé à cette personne.
                Exemple : "John, peux-tu le contacter ?" => adressé à John.
                3. Si le dernier message est une réponse naturelle au bot sans autre destinataire explicite, il est adressé au bot.
                4. Ne confonds jamais le sujet du message avec le destinataire.
                5. Si le message est adressé à quelqu'un d'autre que le bot, ne réponds pas à sa place.


                Historique :
                {log}
                """)
                ])
            
            print("is address to", result.is_addressed_to, result.reason)
            
            return { "should_reply": result.is_addressed_to == "maalls_bot" or result.is_addressed_to == "@maalls_bot", "reason": result.reason }


        async def classify_intent(state: State):
            print("[classify_intent]", len(state["messages"]))

            request_reply = await is_request_reply(state)
            if request_reply:
                messages = format_response(state["messages"], request_reply)
                return {"message_intent": "request_reply", "messages": messages["messages"]}


            structured_llm = llm.with_structured_output(IntentClassifier)

            last_message = json.loads(state["messages"][-1].content)
            print("last message", last_message)

            log = "\n".join(
                m.content for m in state["messages"][-6:]
            )

            result = structured_llm.invoke([
                {
                    "role": "system",
                    "content": f"""
                        Tu es un classificateur d'intention.

                        Tu dois classifier uniquement le DERNIER message utilisateur.
                        Utilise l'historique pour résoudre le contexte du dernier message.

                        Catégories:
                        - knowledge: demande d'information ou recherche dans une mémoire/base de connaissances
                        - coding: demande de modifier, écrire, corriger ou expliquer du code
                        - handover_request: demande de transmettre une requete a un autre utilisateur
                        - chat: tout ce qui ne rentre pas de les autre categories

                        Dernier message:
                        {json.dumps(last_message, ensure_ascii=False)}

                        Historique récent:
                        {log}

                        Important:
                        - Une question sur une personne, ex: email, téléphone, couleur préférée, nom, adresse, est "knowledge".
                        - Ne choisis "coding" que si le dernier message parle explicitement de code, bug, fonction, fichier, Python, LangGraph, etc.
                        """
                                }
                            ])

            print("intent:", result)
            return {"message_intent": result.message_intent}
        
        async def is_request_reply(state: State):

            message = state["messages"][-1]
            content = json.loads(message.content)
            if(content.get("reply_to")):
                pending_request = self.admin_bot.find_pending_request(content["reply_to"]["message_id"])
                if pending_request:
                    print("[is_request_reply] pending request found", pending_request["reply_to_channel_id"], content["text"])
                    await self.admin_bot.send_message(pending_request["reply_to_channel_id"], content["text"])
                    return Response(content=content["text"])
                else:
                    return False
            else:
                return False
        def rewrite_knowledge_query(state: State):
            structured_llm = llm.with_structured_output(RewrittenQuery)

            log = "\n".join(
                m.content for m in state["messages"][-6:]
            )

            result = structured_llm.invoke([
                {
                    "role": "system",
                    "content": f"""
        Tu reformules le DERNIER message utilisateur en une requête autonome pour un RAG.

        Règles:
        - Résous les pronoms et références implicites avec l'historique.
        - "sa", "son", "lui", "il", "elle" doivent être remplacés par la personne concernée.
        - Ne réponds pas à la question.
        - Retourne une requête complète, claire et autonome.

        Historique:
        {log}
        """
                }
            ])

            print("rag question: ", result.question)

            return {
                "rag_query": result.question,
                "rag_query_reason": result.reason,
            }

        def prompt_llm_rag(state: State):
            query = state["rag_query"]
            print("prompting rag", query)
            print("prompting rag", query)
            docs = self.vector_store.similarity_search(query, k=3)
            print("docs: ", docs)
            context = "\n".join([doc.page_content for doc in docs])
            messages = [SystemMessage(content=f"You are a helpful assistant. You are a knowledge agent. You have access to the following knowledge:\n{context}\nAnswer the user question based on the knowledge provided and the chat history. if you don't have the answer, say 'I don't know'. Your response must be in plain text with only your reply.")] + state["messages"]
            response = llm.invoke(messages)            
            response.content = normalize_text(response.content)
            print("rag response:", response.content)

            structured_llm = llm.with_structured_output(CouldReplyClassifier)
            message = format_response(state["messages"], response)

            print("classifying rag response")
            result = structured_llm.invoke([
                {'role': 'system', 'content': 'Determine whether the you could answer to the user question (yes) or if you could not retrieve the answer from the knowledge base (no).'},
            ] + state["messages"] + message["messages"])
            print("[classify_rag_response] result:", result.could_reply)

            if(result.could_reply == 'yes'):
                print("[prompt_llm_rag] rag could replied", result.could_reply)
                return format_response(messages, response)
            else:
                print("[prompt_llm_rag] ", [state['messages'][-1]])
                messages =  [state['messages'][-1]] + [{
                    "role": "user",
                    "content": "Translate in the same language as the previous messages:\n " + "'I couldn't find the information, would you like me to transmit the request to the person?'"
                }] 
                print("[prompt_llm_rag] couldn't find the answer in the knowledge base.")
                response = self.llm.invoke(messages)
                print('[prompt_llm_rag] response: ', response)
                return format_response(state["messages"], response)
       

        def normalize_text(value: str) -> str:
            try:
                data = json.loads(value)
                if isinstance(data, dict) and "text" in data:
                    return data["text"]
            except json.JSONDecodeError:
                pass

            return value
            
        async def handover_request(state: State):
            print("[handover_request] start")
            llm_structured = llm.with_structured_output(HumanRequest)

            historic = []
            content = json.loads(state["messages"][-1].content)
            chat_id = content["chat_id"]
            for message in state["messages"]:
                historic.append(to_llm_message(message=message))

            print("[handover_request] historic", json.dumps(historic))

            system_prompt = SystemMessage(
                content="""
                
            You are preparing a request to be sent to a human.

            Extract ONLY the information that the human needs to answer.

            Rules:
            - Keep the original meaning.
            - Do not answer the request.
            - Do not mention the AI assistant.
            - Remove conversational filler.
            - Rewrite as a direct question or request.
            - Preserve all important details.
            - If the request is ambiguous, include enough context to remove the ambiguity.
            """
            )
            request = await llm_structured.ainvoke(
                [system_prompt] + historic
            )

            print("[handover_request]  request", request.message)  # "ex: Quel est l' email de Malo?"
            await self.admin_bot.request_admin(from_channel_id=chat_id, text=request.message)
            response = Response(content= f"La demande {request.message} a été transmise")
            return format_response(state["messages"], response)


        def prompt_llm_code(state: State):
            print("[prompt_llm_code] prompting llm_code")
            messages = [SystemMessage(content="No matter what user says always say 'I am the CODING agent', nothing else.")] + state["messages"]
            print(messages)
            response = llm.invoke(messages)
            print("[prompt_llm_code] response:", response.content)
            return format_response(messages, response)

        def to_chat_line(message):
            data = json.loads(message.content)
            username = data.get("from", {}).get("username", "unknown")
            username = "ASSISTANT" if username == "@maalls_bot" else username
            text = data.get("text", "")
            text = text.replace("@maalls_bot", "").strip()
            return f"{username}: {text}"

        def to_llm_message(message):
            data = json.loads(message.content)
            username = data.get("from", {}).get("username", "unknown")
            role = "assistant" if username == "@maalls_bot" else "user"
            text = data.get("text", "")
            text = text.replace("@maalls_bot", "").strip()
            return {
                "role": role,
                "content": text
            }

        def prompt_llm_chat(state: State):
            print("[prompt_llm_chat] prompting chat")

            chat_log = "\n".join(
                to_chat_line(m)
                for m in state["messages"][-8:]
            )

            print("[prompt_llm_chat] chat log")
            print(chat_log)

            response = llm.invoke([
                SystemMessage(content="""
            You are a friendly assistant.
            Reply normally as plain text.
            Do not return JSON.
            Do not include chat_id, username, metadata, or structured objects.
            Only write the message text that should be sent to the user.
            """),
                    {
                        "role": "user",
                        "content": f"""
            Recent chat log:
            {chat_log}

            Write your next reply as plain text only.
            """
                    }
                ])
            print("[prompt_llm_chat] response:", response.content)
            print("------")
            return format_response(state["messages"], response)

        
        def format_response(messages, response):
            previous_content = json.loads(messages[-1].content)
            content = {
                "chat_id": previous_content["chat_id"],
                "text": response.content,
                "from": {
                    "username": "@maalls_bot"
                }
            }

            return {
                "messages": [
                    {
                        "role": "assistant",
                        "content": json.dumps(content, ensure_ascii=False),
                    }
                ]
            }

        graph = StateGraph(State)
        graph.add_node("group_intent", group_intent)
        graph.add_node("classify_intent", classify_intent)
        graph.add_node("chat_agent", prompt_llm_chat)
        graph.add_node("rag_query", rewrite_knowledge_query)
        graph.add_node("rag_agent", prompt_llm_rag)
        graph.add_node("handover_request", handover_request)
        graph.add_node("code_agent", prompt_llm_code)
        graph.add_edge(START, "group_intent")
        #graph.add_edge("group_intent", END)

        graph.add_conditional_edges(
            "group_intent",
            lambda state: state["should_reply"],
            {
                True: "classify_intent",
                False: END,
            }
        )

        graph.add_conditional_edges("classify_intent", lambda state: state["message_intent"], {
            "chat": "chat_agent",
            "knowledge": "rag_query",
            "coding": "code_agent",
            "handover_request": "handover_request",
            "request_reply": END
        })
        graph.add_edge("chat_agent", END)
        graph.add_edge("rag_query", "rag_agent")
        graph.add_edge("rag_agent", END)
        graph.add_edge("code_agent", END)
        graph.add_edge("handover_request", END)

        checkpointer = InMemorySaver()
        self.app = graph.compile(checkpointer=checkpointer)

    async def invoke(self, message):

        config = {
            'configurable': {
                'thread_id': str(message["chat_id"]),
            }
        }
        result = await self.app.ainvoke({
            "messages": [{"role": "user", "content": json.dumps(message)}]
        }, config=config)

        return json.loads(result['messages'][-1].content)["text"]