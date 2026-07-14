from langchain_core.messages import SystemMessage
import json
from src.langgraph.format_response import format_response
from src.langgraph.state import State
class ChatNode:
    def __init__(self, llm, admin_username: str):
        self.llm = llm
        self.admin_username = admin_username

    def run(self, state: State):
        print("[prompt_llm_chat] prompting chat")

        chat_log = "\n".join(
            self.to_chat_line(m)
            for m in state["messages"][-8:]
        )

        print("[prompt_llm_chat] chat log")
        print(chat_log)

        response = self.llm.invoke([
            SystemMessage(content="""
        You are a friendly assistant.
        Reply normally in plain text and in a short manner.
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
        
        return {
            "messages": [format_response(state["messages"], response, self.admin_username)]
        }
    
    def to_chat_line(self, message):
        data = json.loads(message.content)
        username = data.get("from", {}).get("username", "unknown")
        username = "ASSISTANT" if username == "@" + self.admin_username else username
        text = data.get("text", "")
        text = text.replace("@" + self.admin_username, "").strip()
        return f"{username}: {text}"