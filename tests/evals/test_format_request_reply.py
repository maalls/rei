import pytest
from tests.evals.test_app import create_test_app

@pytest.mark.asyncio
async def test_format_request_reply():

    # write dummy data to the embeddings storage file for testing
    app = create_test_app()
    result = app.format_request_reply(request="Quelle est la date de naissance de Malo Yamakado?", reply="15 mars 1990.")
    print("result", result)
    assert result == "La date de naissance de Malo Yamakado est le 15 mars 1990."