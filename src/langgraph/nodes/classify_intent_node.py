
from src.langgraph.state import State
from pydantic import BaseModel, Field
from typing import Literal
import json
class IntentClassifier(BaseModel):
    message_intent: Literal['chat', 'knowledge', 'handover_request'] = Field(..., description="Classify whether the user want to just chat, ask for knowledge,  hand over a request to someone else (handover_request)")
    description: str = Field("...", description="A detailed description of what the intent is based on the last message and the log history.")

class ClassifyIntentNode:
    def __init__(self, llm):
        self.llm = llm

    async def run(self, state: State):
        print("[classify_intent] messages: ", len(state["messages"]))

        structured_llm = self.llm.with_structured_output(IntentClassifier)

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
                    par example, si l'assistant a déjà confirmé qu'une demande a été transmise à l'administrateur (handover), passe en mode "chat" et repond si la reponse est disponible dans l'historique sinon dit lui de patienter.
                    Si l'utilisateur pose une question et que la reponse est deja connue par l'assistant, alors le dernier message est une demande de connaissance.
                    Si l’assistant vient de confirmer qu’une demande a été transmise, alors un message comme
                    "ok", "merci", "ok merci", "super", "parfait" est une simple réponse conversationnelle
                    et ne constitue pas une nouvelle demande de transmission.

                    Catégories:
                    - knowledge: demande d'information ou recherche dans une mémoire/base de connaissances
                    - handover_request: demande de transmettre une requete a l'administrateur humain. Fait particulierement attention a regarder l'historique pour determiner si c'est une requete a transmettre ou pas.
                    - chat: tout ce qui ne rentre pas de les autre categories

                    Dernier message:
                    {json.dumps(last_message, ensure_ascii=False)}

                    Historique récent:
                    {log}

                    Important:
                    - Tu dois classifier uniquement l'intention du DERNIER message utilisateur. L'historique est là pour t'aider à comprendre le contexte.
                    - Une question sur une personne, ex: email, téléphone, couleur préférée, nom, adresse, est "knowledge".
                    """
                            }
                        ])

        print("[classify_intent] intent:", result)
        return {"message_intent": result.message_intent}
        