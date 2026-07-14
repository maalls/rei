from types import SimpleNamespace

import pytest
from src.config import settings
from src.factory.factory import Factory
from unittest.mock import AsyncMock
from types import SimpleNamespace


@pytest.mark.asyncio
async def test_double_questions():
    factory = Factory(settings)
    app = factory.create_langgraph_app()
    app.admin_bot.send_message = AsyncMock(
        return_value=SimpleNamespace(
        id=456
    )

    )
    user_message = "@maalls_bot quel est la couleur preferee de malo?"
    message = {
        "chat_id": 123,
        "message_id": 234,
        "chat_type": "group",
        "text": user_message,
        "from": {
            "username": "@toto"
        }
    }
    print("\n")
    print("user: ", user_message)
    result = await app.invoke(message)
    print("assitant:", result)
    assert result == "La couleur préférée de Malo Yamakado est le bleu."

    user_message = "et sa date de naissance?"
    message["text"] = user_message
    print("user: ", user_message)
    result = await app.invoke(message)
    print("assitant:", result)
    assert result == "Je n'ai pas réussi à trouver l'information, voulez-vous que je transmette la demande à mon administrateur ?"

    message["text"] = "oui"
    print("user: ", message["text"])
    result = await app.invoke(message)
    print("assistant: ", result)
    assert result == "La demande Quelle est la date de naissance de Malo Yamakado? a bien été transmise. Je vous tiendrai informé dès que j'aurai une réponse."
    message["text"] = "ok merci"
    print("user: ", message["text"])
    result = await app.invoke(message)
    print("assistant: ", result)

    message["text"] = "Paul, peux tu verifier si maalls_bot a bien transmis la demande ?"
    print("user: ", message["text"])
    result = await app.invoke(message)
    print("assistant: ", result)
    assert result == False

    message["text"] = "chiki chiki?"
    print("user: ", message["text"])
    result = await app.invoke(message)
    print("assistant: ", result)
    assert result == "Ai Ai Ai!!!"
    