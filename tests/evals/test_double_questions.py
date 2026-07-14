from types import SimpleNamespace

import pytest
from test_app import create_test_app, create_test_message
from unittest.mock import AsyncMock
from types import SimpleNamespace


@pytest.mark.asyncio
async def test_double_questions():
    app = create_test_app()
    app.admin_bot.send_message = AsyncMock(
        return_value=SimpleNamespace(
        id=456
    )

    )
    print("\n")
    message = create_test_message("@maalls_bot quel est la couleur preferee de malo?", username="toto")
    print("user: ", message["text"])
    result = await app.invoke(message)
    print("assitant:", result)
    assert result == "La couleur préférée de Malo Yamakado est le bleu."

    message = create_test_message("et sa date de naissance?", username="toto")
    print("user: ", message["text"])
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
    