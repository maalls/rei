
from pydantic import BaseModel, Field
from typing import Literal
class CouldReplyClassification(BaseModel):
    could_reply: Literal['yes', 'no'] = Field(..., description="Classify whether the LLM could find the information to the user requested or not.")

class CouldReplyClassifier:

    def __init__(self, llm):
        self.llm = llm

    def classify(self, user_question: str, assistant_response: str) -> CouldReplyClassification:
        structured_llm = self.llm.with_structured_output(CouldReplyClassification)
        result = structured_llm.invoke([
            {'role': 'system', 'content': f"""
             Determine if the assistant managed to retrieve the answer of the user question  (yes) or not (no).
             user: {user_question}
             assistant: {assistant_response}
             """},
        ])
        return result.could_reply == "yes"