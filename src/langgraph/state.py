from typing import TypedDict, Annotated
from langgraph.graph import add_messages

class State(TypedDict):
    messages: Annotated[list, add_messages]
    is_chikichiki: bool | None
    should_reply: str | None
    reason: str | None
    could_reply: str | None
    rag_query: str
    rag_query_reason: str
    auto_reply: bool = False
