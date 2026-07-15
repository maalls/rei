import re

from src.langgraph.state import State
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage
import json
class GroupIntent(BaseModel):
    addressed_to: str | None = Field(
        description="nom de la personne ou du bot à qui le message est adressé dans le groupe, sans @, ou null si aucun destinataire spécifique."
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
            Identifier qui est censé répondre au dernier message.

            Ne cherche pas la personne dont on parle.
            Cherche la personne à qui la phrase est adressée.   
            Les personnes mentionnées après des verbes comme
            "demande à",
            "dis à",
            "préviens",
            "transmets à",
            "parle à"
            ne sont PAS le destinataire.

            Pour déterminer le destinataire, applique ces règles dans l'ordre :

            1. Si une personne est explicitement interpellée au début du message
            ("@Bot", "Paul,", etc.), c'est le destinataire.

            2. Sinon, si le message est une réponse naturelle au message précédent,
            alors le destinataire est l'auteur du message précédent.

            3. Sinon, si le message poursuit clairement une conversation récente
            entre deux personnes, le destinataire est l'autre participant.

            4. Sinon, considère qu'il n'y a pas de destinataire identifiable.

            examples:
            {{from: @toto, text:"@Bot demande à Paul quelle heure il est"}}
            => destinataire = Bot

            {{from: @toto, text:"Paul, dis à Jean bonjour"}}
            => destinataire = Paul

            {{from: @toto, text:"@Bot peux-tu demander à Malo..."}}
            => destinataire = Bot

            {{from: @toto, text:"Jean, demande à Paul..."}}
            => destinataire = Jean     
            Messages PRÉCÉDENTS du plus ancien au plus récent:
            {log or "(aucun message précédent)"}
            dernier message:
            {k} - {last_message}
            """
        print("[group_intent] prompt:", prompt)
        result = structured_llm.invoke([
                SystemMessage(content=prompt)
            ])
        
        print("[group_intent] addressed to:", result.addressed_to, "reason:", result.reason)
        
        return { "should_reply": result.addressed_to == self.bot_username or result.addressed_to == "@"+self.bot_username, "addressed_to": result.addressed_to, "reason": result.reason }
