import re

from src.langgraph.state import State
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage
import json
class GroupIntent(BaseModel):
    should_reply: bool | None = Field(
        description="TRUE si le bot doit répondre, FALSE sinon."
    )
    reason: str | None = Field(
        description="Raison pour laquelle le bot doit répondre ou non."
    )

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

        m = re.match(r'^\s*@([A-Za-z0-9_]+)', message['text'])
        if m:
            addressed_to = m.group(1)
            if addressed_to.lower() == self.bot_username.lower():
                print(f"[group_intent] message starts with @{self.bot_username} so should reply")
                return {
                    "should_reply": True,
                    "reason": f"Le dernier message commence par: @{self.bot_username}.",
                }
            else:
                print(f"[group_intent] message starts with @{addressed_to} so should not reply")
                return {
                    "should_reply": False,
                    "reason": f"Le dernier message commence par: @{addressed_to}.",
                }
        print("[group_intent] content reply",state.get("auto_reply"), not state.get("auto_reply"))
        if(not state.get("auto_reply")):
            print("[group_intent] auto_reply is false so bot should not reply")
            return {
                "should_reply": False,
                "reason": "Le flag auto_reply est false et le dernier message n'est pas une réponse à un message du bot.",
            }
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
            Tu incarnes uniquement {self.bot_username}.

            Les autres bots, usernames et personnes sont des destinataires distincts.
            Si le message mentionne explicitement un autre bot ou une autre personne, {self.bot_username} ne doit pas répondre, même si la question poursuit une conversation précédente avec lui.

            Une mention explicite est prioritaire sur le contexte de la conversation.
            Réponds uniquement par :

            should_reply: true|false
            reason: ...

            Le bot doit répondre si :

            - on lui parle directement ;
            - une question poursuit naturellement une conversation avec lui ;
            - une réponse est clairement destinée au bot.

            Le bot ne répond pas si les utilisateurs parlent entre eux.  
            Messages PRÉCÉDENTS du plus ancien au plus récent (from est l'autheur du message, et text est le contenu du message) :
            {log or "(aucun message précédent)"}
            dernier message:
            {k} - {last_message}
            """
        print("[group_intent] prompt:", prompt)
        result = structured_llm.invoke([
                SystemMessage(content=prompt)
            ])
        
        print("[group_intent] should_reply:", result.should_reply, "reason:", result.reason)
        
        return { "should_reply": result.should_reply, "reason": result.reason }
