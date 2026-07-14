from datetime import date
import time
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
    message_intent: Literal['chat', 'knowledge', 'handover_request', 'chikichiki'] = Field(..., description="Classify whether the user want to just chat, ask for knowledge,  hand over a request to someone else (handover_request) or cheerfully reply 'ay ay ay' when saying 'chiki chiki' (chikichiki).")
    description: str = Field("...", description="A detailed description of what the intent is based on the last message and the log history.")

class GroupIntent(BaseModel):
    addressed_to: str | None = Field(
        description="Username du destinataire supposé, sans @, ou null si aucun destinataire spécifique."
    )
    reason: str

class RewrittenQuery(BaseModel):
    question: str
    reason: str

class Response(BaseModel):
    content: str | None
    
class State(TypedDict):
    messages: Annotated[list, add_messages]
    is_chikichiki: bool | None
    should_reply: str | None
    reason: str | None
    could_reply: str | None
    rag_query: str
    rag_query_reason: str

class CouldReplyClassifier(BaseModel):
    could_reply: Literal['yes', 'no'] = Field(..., description="Classify whether the LLM could find the information to the user requested or not.")

class ChikiChikiClassifier(BaseModel):
    is_chikichiki: bool = Field(..., description="Classify whether the last message is a 'chiki chiki' or not. If it is, return True, otherwise return False.")
    content: str = "Ai Ai Ai!!!"
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

        def group_intent(state: State):

            print("[group_intent] messages:", len(state["messages"]))

            last = json.loads(state["messages"][-1].content)
            last_text = last.get("text", "")                

            if(last["chat_type"] == "private"):
                print("[group_intent] it's a private chat so bot should reply")
                return {
                    "should_reply": True,
                    "reason": "it's a private chat so bot should reply"
                }

            if "@" + self.admin_bot.username in last_text.lower():
                print(f"[group_intent] @{self.admin_bot.username} is mentioned in the message so should reply")
                return {
                    "should_reply": True,
                    "reason": f"Le dernier message mentionne explicitement: @{self.admin_bot.username}.",
                }

            structured_llm = llm.with_structured_output(GroupIntent)

            message = json.loads(state["messages"][-1].content)
            last_message = f"{{ from: '{message['from']['username']}', text: {json.dumps(message['text'], ensure_ascii=False)} }}"
            print("[group_intent] last message", last_message)

            previous_messages = state["messages"][:-1]

            logs = []
            k = 1
            for state_message in previous_messages[-10:]:
                parsed = json.loads(state_message.content)

                username = parsed.get("from", {}).get("username") or "unknown"
                text = parsed.get("text", "")

                logs.append(
                    f"{k} - {{ from: '{username}', text: {json.dumps(text, ensure_ascii=False)} }}"
                )
                k += 1

            log = "\n".join(logs)

            prompt = f"""
                Ton rôle est d’identifier la personne ou le bot à qui l’auteur parle
                dans le dernier message.

                Ne cherche pas la personne dont on parle.
                Cherche la personne à qui la phrase est adressée.        
                Messages PRÉCÉDENTS du plus ancien au plus récent:
                {log or "(aucun message précédent)"}
                dernier message:
                {k+1} - {last_message}
                """
            print("[group_intent] prompt:", prompt)
            result = structured_llm.invoke([
                    SystemMessage(content=prompt)
                ])
            
            print("[group_intent] addressed to:", result.addressed_to, "reason:", result.reason)
            
            return { "should_reply": result.addressed_to == self.admin_bot.username or result.addressed_to == "@"+self.admin_bot.username, "addressed_to": result.addressed_to, "reason": result.reason }

        async def classify_intent(state: State):
            print("[classify_intent] messages: ", len(state["messages"]))

            request_reply = await is_request_reply(state)
            if request_reply:
                messages = format_response(state["messages"], request_reply)
                return {"message_intent": "request_reply", "messages": messages["messages"]}

            structured_llm = llm.with_structured_output(IntentClassifier)

            message = json.loads(state["messages"][-1].content)
            last_message = f"{message['from']['username']} said: {message['text']}"
            print("[classify_intent] last message", last_message)

            logs = []
            for message in state["messages"]:
                message = json.loads(message.content)
                logs.append(f"{message['from']['username']} said: {message['text']}")
            
            log = "\n".join(logs)
            
            print("[classify_intent] log history:")
            for l in logs:
                print("[classify_intent] - ", l)

            result = structured_llm.invoke([
                {
                    "role": "system",
                    "content": f"""
                        Tu es un classificateur d'intention.

                        Tu dois classifier le DERNIER message utilisateur.
                        Utilise l'historique pour résoudre le contexte du dernier message.

                        Le dernier message est la seule source de l’intention actuelle.

                        L’historique sert uniquement à résoudre les références et comprendre le contexte.

                        Ne réutilise pas l’intention d’un message précédent si cette action a déjà été accomplie.
                        par example, si l'assistant a déjà confirmé qu'une demande a été transmise à l'administrateur, il ne faut pas considérer que le dernier message est une nouvelle demande de transmission.
                        Si l'utilisateur pose une question et que la reponse est deja connue par l'assistant, alors le dernier message est une demande de connaissance.
                        Si l’assistant vient de confirmer qu’une demande a été transmise, alors un message comme
                        "ok", "merci", "ok merci", "super", "parfait" est une simple réponse conversationnelle
                        et ne constitue pas une nouvelle demande de transmission.

                        Catégories:
                        - knowledge: demande d'information ou recherche dans une mémoire/base de connaissances
                        - coding: demande de modifier, écrire, corriger ou expliquer du code
                        - handover_request: demande de transmettre une requete a l'administrateur humain. Fait particulierement attention a regarder l'historique pour determiner si c'est une requete a transmettre ou pas.
                        - chat: tout ce qui ne rentre pas de les autre categories

                        Dernier message:
                        {json.dumps(last_message, ensure_ascii=False)}

                        Historique récent:
                        {log}

                        Important:
                        - Tu dois classifier uniquement l'intention du DERNIER message utilisateur. L'historique est là pour t'aider à comprendre le contexte.
                        - Une question sur une personne, ex: email, téléphone, couleur préférée, nom, adresse, est "knowledge".
                        - Ne choisis "coding" que si le dernier message parle explicitement de code, bug, fonction, fichier, Python, LangGraph, etc.
                        """
                                }
                            ])

            print("[classify_intent] intent:", result)
            return {"message_intent": result.message_intent}
        
        async def is_request_reply(state: State):

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
                        "text": text,
                        "from": {
                            "username": "@" + self.admin_bot.username,
                        },
                        "date": date.today().isoformat(),
                        "timestamp": int(time.time()),
                    }
                    await self.app.aupdate_state(
                        config={
                            "configurable": {
                                "thread_id": str(pending_request["reply_to_channel_id"]),
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

                    self.admin_bot.remove_pending_request(message_id=message_id)
                    self.store_new_knowledge(text=text)
                    return Response(content=text)
                else:
                    return False
            else:
                return False
            
        

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

        def prompt_llm_rag(state: State):
            query = state["rag_query"]
            print("[prompting rag] query:", query)
            docs = self.vector_store.similarity_search(query, k=5)
            print("[prompt_llm_rag] docs: (", len(self.vector_store.store), " total docs)")

            for doc in docs:
                print("[prompt_llm_rag] doc ", doc.page_content) 
            context = "\n".join([doc.page_content for doc in docs])
            messages = [SystemMessage(content=f"You are a helpful assistant. You are a knowledge agent. You have access to the following knowledge:\n{context}\nAnswer the user question based on the knowledge provided and the chat history. if you don't have the answer, say 'I don't know'. Your response must be in plain text with only your reply. Answer in the same language as the user question.")] + state["messages"]
            response = llm.invoke(messages)            
            response.content = normalize_text(response.content)
            print("[prompt_llm_rag] response:", response.content)

            structured_llm = llm.with_structured_output(CouldReplyClassifier)
            message = format_response(state["messages"], response)

            result = structured_llm.invoke([
                {'role': 'system', 'content': 'Determine whether the you could answer to the user question (yes) or if you could not retrieve the answer from the knowledge base (no).'},
            ] + state["messages"] + message["messages"])
            print("[classify_rag_response] result:", result.could_reply)

            if(result.could_reply == 'yes'):
                print("[prompt_llm_rag] rag could replied: ", result.could_reply)
                return format_response(messages, response)
            else:
                messages =  [state['messages'][-1]] + [{
                    "role": "user",
                    "content": "Translate in the same language as the previous messages (do not use quote or any formatting):\n " + "'I couldn't find the information, would you like me to transmit the request to my admin?'"
                }] 
                print("[prompt_llm_rag] couldn't find the answer in the knowledge base.")
                response = self.llm.invoke(messages)
                print('[prompt_llm_rag] response: ', response.content)
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

            
            content = json.loads(state["messages"][-1].content)
            chat_id = content["chat_id"]
            message_id = content["message_id"]

            rewritten_query = state["rag_query"]
            if not rewritten_query:
                print("[handover_request] no rag query found, using last message text")
                llm_structured = llm.with_structured_output(HumanRequest)

                historic = []
                content = json.loads(state["messages"][-1].content)
                chat_id = content["chat_id"]
                
                for message in state["messages"]:
                    historic.append(to_llm_message(message=message))

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
            username = "ASSISTANT" if username == "@" + self.admin_bot.username else username
            text = data.get("text", "")
            text = text.replace("@" + self.admin_bot.username, "").strip()
            return f"{username}: {text}"

        def to_llm_message(message):
            data = json.loads(message.content)
            username = data.get("from", {}).get("username", "unknown")
            role = "assistant" if username == "@" + self.admin_bot.username else "user"
            text = data.get("text", "")
            text = text.replace("@" + self.admin_bot.username, "").strip()
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
            Reply in the same language as the user question.
                              
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

        def handle_chikichiki(state: State):

            print("[handle_chikichiki] handling chiki chiki")
            prompt = "You are classifying whether the user is saying 'chiki chiki' or not. If user saying 'chiki chiki', return True, otherwise return False."
            structured_llm = llm.with_structured_output(ChikiChikiClassifier)
            response = structured_llm.invoke([
                SystemMessage(content=prompt),
                {
                    "role": "user",
                    "content": json.loads(state["messages"][-1].content)["text"]
                }
            ])
            if response.is_chikichiki:
                print("the message is a chiki chiki, returning Ai Ai Ai!!!")
                response.content = "Ai Ai Ai!!!"
                messages = format_response(state["messages"], response)
                return { "is_chikichiki": True, "should_reply": True, "messages": messages["messages"] }
            else:
                return { "is_chikichiki": False }
        
        def format_response(messages, response):
            previous_content = json.loads(messages[-1].content)
            content = {
                "chat_id": previous_content["chat_id"],
                "text": response.content,
                "from": {
                    "username": "@" + self.admin_bot.username
                },
                "date": date.today().isoformat(),
                "timestamp": int(time.time())
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
        graph.add_node("chikichiki", handle_chikichiki)

        graph.add_node("group_intent", group_intent)
        graph.add_node("classify_intent", classify_intent)
        graph.add_node("chat_agent", prompt_llm_chat)
        graph.add_node("rag_query", rewrite_knowledge_query)
        graph.add_node("rag_agent", prompt_llm_rag)
        graph.add_node("handover_request", handover_request)
        graph.add_node("code_agent", prompt_llm_code)
        graph.add_edge(START, "chikichiki")
        #graph.add_edge("group_intent", END)

        graph.add_conditional_edges(
            "chikichiki", lambda state: state["is_chikichiki"], {
                True: END,
                False: "group_intent"
            }
        )
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
            "request_reply": END,
            "chikichiki": "chikichiki"
        })
        graph.add_edge("chat_agent", END)
        graph.add_edge("rag_query", "rag_agent")
        graph.add_edge("rag_agent", END)
        graph.add_edge("code_agent", END)
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
        
    def store_new_knowledge(self, text: str):
        print("[store_new_knowledge] storing new knowledge:", text)
        self.vector_store.add_new_text(text)


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
        print("[format_request_reply] result:", result.formatted_reply)
        return result.formatted_reply