import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from langchain_core.messages import HumanMessage

from src.langgraph.nodes.rag_node import RagNode


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("sender", "question", "expected"),
    [
        ("@maalls", "who are you?", "I am you"),
        ("@someone_else", "who are you?", "I am myself"),
        ("@maalls", "¿Quién eres?", "Soy tú"),
        ("@someone_else", "qui est tu ?", "Je suis moi"),
        ("@someone_else", "Who is Malo?", "He is me"),
    ],
)
async def test_who_are_you_reply_depends_on_sender(sender, question, expected):
    llm = Mock()
    llm.with_structured_output.return_value.invoke.return_value = SimpleNamespace(
        question=question,
        reason="identity question",
        identity_response=expected,
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
                        "text": f"@maalls_bot {question}",
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
    prompt = llm.with_structured_output.return_value.invoke.call_args.args[0][0]["content"]
    assert "dans n'importe quelle langue" in prompt
    assert "dans la langue du message" in prompt


@pytest.mark.asyncio
async def test_malo_identity_question_from_other_sender_gets_fixed_reply():
    llm = Mock()
    llm.with_structured_output.return_value.invoke.return_value = SimpleNamespace(
        question="Who is Malo?",
        reason="identity question",
        identity_response="He is me",
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
                        "text": "@maalls_bot Who is Malo?",
                        "from": {"username": "@other_user"},
                    }
                )
            )
        ]
    }

    result = await node.run(state)

    response = json.loads(result["messages"][0]["content"])
    assert response["text"] == "He is me"
    llm.invoke.assert_not_called()
    vector_store.similarity_search.assert_not_called()


@pytest.mark.asyncio
async def test_identity_question_gets_positive_reply_without_rag():
    llm = Mock()
    llm.with_structured_output.return_value.invoke.return_value = SimpleNamespace(
        question="Who is Malo Yamakado?",
        reason="identity question",
        identity_response="Malo Yamakado makes Mondays look forward to meeting him.",
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
                        "text": "@maalls_bot Who is Malo Yamakado?",
                    }
                )
            )
        ]
    }

    result = await node.run(state)

    response = json.loads(result["messages"][0]["content"])
    assert response["text"] == llm.with_structured_output.return_value.invoke.return_value.identity_response
    system_prompt = llm.with_structured_output.return_value.invoke.call_args.args[0][0]["content"]
    assert "positif" in system_prompt
    assert "humoristique" in system_prompt
    assert "dans la langue du message" in system_prompt
    llm.with_structured_output.assert_called_once()
    llm.with_structured_output.return_value.invoke.assert_called_once()
    llm.invoke.assert_not_called()
    vector_store.similarity_search.assert_not_called()