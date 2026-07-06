import uuid
from typing import TypedDict, Annotated, Literal
from pydantic import BaseModel, Field

from typing import TypedDict
from langgraph.graph import MessagesState, StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph.message import add_messages
from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
from src.langgraph.nomic_vector_store import NomicVectorStore

class IntentClassifier(BaseModel):
    message_intent: Literal['chat', 'knowledge', 'coding', 'ask_human'] = Field(..., description="Classify whether the user want to just chat, ask for knowledge, change code in the project, or ask a human a question (ask_human).")

class State(TypedDict):
    messages: Annotated[list, add_messages]
    message_intent: str | None
    could_reply: str | None

class CouldReplyClassifier(BaseModel):
    could_reply: Literal['yes', 'no'] = Field(..., description="Classify whether the LLM could find the information to the user requested or not.")

class LangGraphApp:
    def __init__(self, 
                 llm: ChatOpenAI, 
                 vector_store: NomicVectorStore,
                 
                 ):
        self.llm = llm
        self.vector_store = vector_store

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

        def classify_intent(state: State): 
            print("[classify_intent]", len(state["messages"]))
            structured_llm = llm.with_structured_output(IntentClassifier)
            result = structured_llm.invoke([
                {'role': 'system', 'content': 'Determine / Classify whether the user want to chat ("chat"), retrieve knowledge ("knowledge"), change code ("coding") or if the user wants you to transmit an information to another user ("ask_human").'},
            ] + state["messages"])
            print("result:", result)
            return {"message_intent": result.message_intent}


        def prompt_llm_chat(state: State):
            print("prompting chat")
            messages = [SystemMessage(content="You are a helpful assistant. You are a talkative agent for fun. Be nice.")] + state["messages"]
            response = llm.invoke(messages)
            return {"messages": [{'role': 'assistant', 'content': response.content}]}

        def prompt_llm_rag(state: State):
            print("prompting rag")
            query = state["messages"][-1].content
            docs = self.vector_store.similarity_search(query, k=3)
            print("docs:", docs)
            context = "\n".join([doc.page_content for doc in docs])
            messages = [SystemMessage(content=f"You are a helpful assistant. You are a knowledge agent. You have access to the following knowledge:\n{context}\nAnswer the user question based on the knowledge provided. If the answer is not in the knowledge, say 'I don't know'.")] + state["messages"]
            response = llm.invoke(messages)
            print("rag response:", response.content)
            return {"messages": [{'role': 'assistant', 'content': response.content}]}

        def classify_rag_response(state: State):
            structured_llm = llm.with_structured_output(CouldReplyClassifier)
            print("classifying rag response")
            result = structured_llm.invoke([
                {'role': 'system', 'content': 'Determine whether the LLM could answer to the user question (yes) or if he could not retrieve the answer from the knowledge base (no).'},
            ] + state["messages"])
            print("[classify_rag_response] result:", result.could_reply)
            return {"could_reply": result.could_reply == 'yes'}
        
        def formulate_rag_response(state: State):
            if(state['could_reply']):
                return
            else:
                messages = [state['messages'][-1]] + [{
                    "role": "user",
                    "content": "Translate in the same language as the previous messages:\n " + "I couldn't find the information, would you like me to transmit the request to the person?"
                }]
                print("couldn't find the answer in the knowledge base.")
                response = self.llm.invoke(messages)
                print('response', response.content)
                return {"messages": [{'role': 'assistant', 'content': response.content}]}
            

        def ask_human(state: State):
            print("asking human")
            return {"messages": [{'role': 'assistant', 'content': "La demande a été transmise."}]}


        def prompt_llm_code(state: State):
            print("prompting llm_code")
            messages = [SystemMessage(content="No matter what user says always say 'I am the CODING agent', nothing else.")] + state["messages"]
            print(messages)
            response = llm.invoke(messages)
            print("response:", response.content)
            return {"messages": [{'role': 'assistant', 'content': "I am the CODING agent"}]}


        def run(self, user_message, config):
            result = self.langgraph.invoke({
                "messages": [{"role": "user", "content": user_message}]
            }, config=config)

            print(result["messages"][-1].content)

        graph = StateGraph(State)
        graph.add_node("classify_intent", classify_intent)
        graph.add_node("chat_agent", prompt_llm_chat)
        graph.add_node("rag_agent", prompt_llm_rag)
        graph.add_node("ask_human", ask_human)
        graph.add_node("classify_rag_response", classify_rag_response)
        graph.add_node("formulate_rag_response", formulate_rag_response)
        graph.add_node("code_agent", prompt_llm_code)
        graph.add_edge(START, "classify_intent")
        graph.add_conditional_edges("classify_intent", lambda state: state["message_intent"], {
            "chat": "chat_agent",
            "knowledge": "rag_agent",
            "coding": "code_agent",
            "ask_human": "ask_human"
        })
        graph.add_edge("chat_agent", END)
        graph.add_edge("rag_agent", "classify_rag_response")
        
        graph.add_edge("classify_rag_response", "formulate_rag_response")
        graph.add_edge("formulate_rag_response", END)
        graph.add_edge("code_agent", END)
        graph.add_edge("ask_human", END)

        checkpointer = InMemorySaver()
        self.app = graph.compile(checkpointer=checkpointer)
        self.config = {
            'configurable': {
                'thread_id': str(uuid.uuid4()),
            }
        }

    def invoke(self, user_message):
        result = self.app.invoke({
            "messages": [{"role": "user", "content": user_message}]
        }, config=self.config)

        return result["messages"][-1].content