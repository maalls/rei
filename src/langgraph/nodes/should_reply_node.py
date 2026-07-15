from src.langgraph.state import State
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage
import json
class GroupIntent(BaseModel):
    addressed_to: str | None = Field(
        description="Username du destinataire supposé, sans @, ou null si aucun destinataire spécifique."
    )
    reason: str

class ShouldReplyNode:
    def __init__(self, llm, bot_username):
        self.llm = llm
        self.bot_username = bot_username
    def run(self, state: State):
        print("[group_intent] messages:", len(state["messages"]))

        last = json.loads(state["messages"][-1].content)
        last_text = last.get("text", "")                

        if(last["chat_type"] == "private"):
            print("[group_intent] it's a private chat so bot should reply")
            return {
                "should_reply": True,
                "reason": "it's a private chat so bot should reply"
            }

        if "@" + self.bot_username in last_text.lower():
            print(f"[group_intent] @{self.bot_username} is mentioned in the message so should reply")
            return {
                "should_reply": True,
                "reason": f"Le dernier message mentionne explicitement: @{self.bot_username}.",
            }

        structured_llm = self.llm.with_structured_output(GroupIntent)

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
        
        return { "should_reply": result.addressed_to == self.bot_username or result.addressed_to == "@"+self.bot_username, "addressed_to": result.addressed_to, "reason": result.reason }
