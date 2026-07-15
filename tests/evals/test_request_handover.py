from types import SimpleNamespace
import pytest
from tests.evals.test_app import create_test_app
from unittest.mock import AsyncMock
from types import SimpleNamespace

@pytest.mark.asyncio
async def test_request_handover():
    
    app = create_test_app()
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
    admin_name = app.admin_bot.get_admin_info()["display_name"]
    assert result == f"Je n'ai pas trouvé d'informations, voulez-vous que je transmette la demande à {admin_name} ?"
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
    assert result == "Ai Ai Ai!"




    