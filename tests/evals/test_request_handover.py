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

    message = {
        "chat_id": 123,
        "message_id": 234,
        "chat_type": "group",
        "text": "@maalls_bot quel est l'age de Malo",
        "from": {
            "username": "@maalls"
        }
    }
    result = await app.invoke(message)
    assert result == "Je n'ai pas trouvé d'informations à ce sujet. Voulez-vous que je transmette cette requête à la personne ?"
    message["text"] = "oui"

    result = await app.invoke(message)

    print("result2: ", result)

    admin_chat_id = app.admin_bot.get_admin_chat_id()
    message = {
        "chat_id": admin_chat_id,
        "chat_type": "private",
        "text": "47 ans",
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

    assert result == "Ai Ai Ai!!!"




    