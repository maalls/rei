
from src.langgraph.state import State
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage
import json
from src.langgraph.format_response import format_response
class ChikiChikiClassifier(BaseModel):
    is_chikichiki: bool = Field(..., description="Classify whether the last message is a 'chiki chiki' or not. If it is, return True, otherwise return False.")
    content: str = "Ai Ai Ai!"

class ChikiChikiNode:

    def __init__(self, llm, admin_username: str | None = None):
        self.llm = llm
        self.admin_username = admin_username

    def run(self, state: State):

            print("[handle_chikichiki] handling chiki chiki")
            prompt = "You are classifying whether the user is saying 'chiki chiki' or not. If user saying 'chiki chiki', return True, otherwise return False."
            structured_llm = self.llm.with_structured_output(ChikiChikiClassifier)
            response = structured_llm.invoke([
                SystemMessage(content=prompt),
                {
                    "role": "user",
                    "content": json.loads(state["messages"][-1].content)["text"]
                }
            ])
            if response.is_chikichiki:
                print("the message is a chiki chiki, returning Ai Ai Ai!!!")
                response.content = "Ai Ai Ai!"
                message = format_response(state["messages"], response, self.admin_username)
                return { "is_chikichiki": True, "should_reply": True, "messages": [message] }
            else:
                return { "is_chikichiki": False }