import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from langchain_core.messages import HumanMessage

from src.langgraph.nodes.rag_node import RagNode


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("sender", "question", "identity_kind", "name", "compliment", "expected"),
    [
        ("@maalls", "who are you?", "who_are_you", None, None, "je suis toi"),
        (
            "@someone_else",
            "who are you?",
            "who_are_you",
            None,
            "un assistant si modeste que même son miroir lui demande des conseils",
            "je suis moi, un assistant si modeste que même son miroir lui demande des conseils",
        ),
        ("@maalls", "¿Quién eres?", "who_are_you", None, None, "je suis toi"),
        (
            "@someone_else",
            "qui est tu ?",
            "who_are_you",
            None,
            "un concentré de bonne humeur avec un bouton pause introuvable",
            "je suis moi, un concentré de bonne humeur avec un bouton pause introuvable",
        ),
        ("@someone_else", "Who is Malo?", "who_is_person", "Malo", None, "il est moi"),
        (
            "@someone_else",
            "Qui est Roger ?",
            "who_is_person",
            "Roger",
            "un rayon de soleil avec le sens du timing d'un humoriste. Même son ombre rit avant la chute.",
            "Roger est un rayon de soleil avec le sens du timing d'un humoriste. Même son ombre rit avant la chute.",
        ),
        ("@maalls", "Qui suis-je ?", "who_am_i", None, None, "je suis toi"),
        (
            "@alice",
            "Qui suis-je ?",
            "who_am_i",
            None,
            "capable de transformer une réunion ennuyeuse en sitcom primée. Même ton agenda prend des notes pour apprendre à être aussi drôle.",
            "tu es capable de transformer une réunion ennuyeuse en sitcom primée. Même ton agenda prend des notes pour apprendre à être aussi drôle.",
        ),
    ],
)
async def test_identity_question_gets_rule_based_reply(sender, question, identity_kind, name, compliment, expected):
    llm = Mock()
    llm.with_structured_output.return_value.invoke.return_value = SimpleNamespace(
        question=question,
        reason="identity question",
        identity_kind=identity_kind,
        identity_name=name,
        identity_compliment=compliment,
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
    assert 'identity_kind="who_am_i"' in prompt
    assert 'identity_kind="who_are_you"' in prompt
    assert 'identity_kind="who_is_person"' in prompt


@pytest.mark.asyncio
async def test_malo_identity_question_from_other_sender_gets_fixed_reply():
    llm = Mock()
    llm.with_structured_output.return_value.invoke.return_value = SimpleNamespace(
        question="Who is Malo?",
        reason="identity question",
        identity_kind="who_is_person",
        identity_name="Malo",
        identity_compliment=None,
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
    assert response["text"] == "il est moi"
    llm.invoke.assert_not_called()
    vector_store.similarity_search.assert_not_called()


@pytest.mark.asyncio
async def test_identity_question_gets_positive_reply_without_rag():
    llm = Mock()
    llm.with_structured_output.return_value.invoke.return_value = SimpleNamespace(
        question="Who is Malo Yamakado?",
        reason="identity question",
        identity_kind="who_is_person",
        identity_name="Malo Yamakado",
        identity_compliment="the kind of person who makes Mondays ask for an encore.",
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
    assert response["text"] == (
        "Malo Yamakado est "
        + llm.with_structured_output.return_value.invoke.return_value.identity_compliment
    )
    system_prompt = llm.with_structured_output.return_value.invoke.call_args.args[0][0]["content"]
    assert "identity_compliment contient UNIQUEMENT le compliment" in system_prompt
    llm.with_structured_output.assert_called_once()
    llm.with_structured_output.return_value.invoke.assert_called_once()
    llm.invoke.assert_not_called()
    vector_store.similarity_search.assert_not_called()