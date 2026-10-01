import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from langchain_core.messages import HumanMessage

from src.langgraph.nodes.rag_node import RagNode


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("sender", "expected"),
    [("@maalls", "je suis toi"), ("@someone_else", "je suis moi")],
)
async def test_who_are_you_reply_depends_on_sender(sender, expected):
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
                        "text": "@maalls_bot qui es-tu ?",
                        "from": {"username": sender},
                    }
                )
            )
        ]
    }

    result = await node.run(state)

    response = json.loads(result["messages"][0]["content"])
    assert response["text"] == expected
    llm.invoke.assert_not_called()
    vector_store.similarity_search.assert_not_called()


@pytest.mark.asyncio
async def test_malo_identity_question_from_other_sender_gets_fixed_reply():
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
                        "text": "@maalls_bot Qui est Malo ?",
                        "from": {"username": "@other_user"},
                    }
                )
            )
        ]
    }

    result = await node.run(state)

    response = json.loads(result["messages"][0]["content"])
    assert response["text"] == "il est moi"
    llm.invoke.assert_not_called()
    vector_store.similarity_search.assert_not_called()


@pytest.mark.asyncio
async def test_identity_question_gets_positive_reply_without_rag():
    llm = Mock()
    llm.invoke.return_value = SimpleNamespace(
        content="Malo Yamakado, c'est le genre de personne qui rend même les lundis sympathiques."
    )
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
    assert response["text"] == llm.invoke.return_value.content
    system_prompt = llm.invoke.call_args.args[0][0].content
    assert "positive" in system_prompt
    assert "humoristique" in system_prompt
    assert "différente" in system_prompt
    llm.with_structured_output.assert_not_called()
    vector_store.similarity_search.assert_not_called()