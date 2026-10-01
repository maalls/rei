import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from langchain_core.messages import HumanMessage

from src.langgraph.nodes.rag_node import RagNode


@pytest.mark.asyncio
async def test_identity_question_gets_positive_reply_without_rag():
    llm = Mock()
    vector_store = Mock()
    node = RagNode(
        llm=llm,
        vector_store=vector_store,
        admin_bot=SimpleNamespace(username="maalls_bot"),
    )
    state = {
        "messages": [
            HumanMessage(
                content=json.dumps(
                    {
                        "chat_id": 123,
                        "text": "@maalls_bot Qui est Malo Yamakado ?",
                    }
                )
            )
        ]
    }

    result = await node.run(state)

    response = json.loads(result["messages"][0]["content"])
    assert response["text"] == "Malo Yamakado est quelqu'un de formidable."
    llm.with_structured_output.assert_not_called()
    vector_store.similarity_search.assert_not_called()