from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from tests.evals.test_app import create_test_app, create_test_message

@pytest.mark.asyncio
async def test_storing_new_knowledge():
    
    app = create_test_app()
    app.admin_bot.send_message = AsyncMock(
        return_value=SimpleNamespace(
        id=456
    )

    )
    message = create_test_message("@maalls_bot quel est l'age de Malo", username="toto")
    print("user: ", message["text"])
    result = await app.invoke(message)
    print("assitant:", result)
    assert result == "Je n'ai pas trouvé d'informations, voulez-vous que je transmette la demande à mon administrateur ?"
    message["text"] = "oui"
    print("user: ", message["text"])
    result = await app.invoke(message)
    print("assistant: ", result)
    # sending the answer to the admin
    message = create_test_message("47 ans", username="toto", chat_id=app.admin_bot.get_admin_chat_id(), chat_type="private", reply_to_message_id=456)
    print("user: ", message["text"])
    result = await app.invoke(message)
    print("assistant: ", result)
    assert result == "L'âge de Malo est 47 ans."

    message = create_test_message("@maalls_bot quel est l'age de Malo", username="toto")
    print("user: ", message["text"])
    result = await app.invoke(message)
    print("assitant:", result)
    
