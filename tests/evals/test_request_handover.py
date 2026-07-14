from types import SimpleNamespace

import pytest
from src.config import settings
from src.factory.factory import Factory
from unittest.mock import AsyncMock
from types import SimpleNamespace


@pytest.mark.asyncio
async def test_admin_answer_formatting():
    factory = Factory(settings)
    app = factory.create_langgraph_app()
    app.admin_bot.send_message = AsyncMock(
        return_value=SimpleNamespace(
        id=456
    )

    )
    user_message = "@maalls_bot quel est l'age de Malo"
    message = {
        "chat_id": 123,
        "message_id": 234,
        "chat_type": "group",
        "text": user_message,
        "from": {
            "username": "@maalls"
        }
    }
    print("\n")
    print("user: ", user_message)
    result = await app.invoke(message)
    print("assitant:", result)
    assert result == "Je n'ai pas trouvé les informations, aimerais-tu que je transmette cette requête à mon administrateur ?"
    message["text"] = "oui"
    print("user: ", message["text"])
    result = await app.invoke(message)

    print("assistant: ", result)

    user_message = "47 ans"
    print(user_message)
    admin_chat_id = app.admin_bot.get_admin_chat_id()
    message = {
        "chat_id": admin_chat_id,
        "chat_type": "private",
        "text": user_message,
        "reply_to": {
            "message_id": 456
        },
        "from": {
            "username": "@maalls"
        }
    }

    result = await app.invoke(message)

    print("result3:", result)

    message = {
        "chat_id": 123,
        "chat_type": "group",
        "text": "Chiki Chiki?",
        "reply_to": None,
        "from": {
            "username": "@maalls"
        }
    }

    result = await app.invoke(message)
    print(result)
    assert result == "Ai Ai Ai!!!"




    