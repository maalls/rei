
import pytest
from src.config import settings
from src.factory.factory import Factory


@pytest.mark.evals
def test_llm_service_chat():
    llm_service = Factory(settings).create_llm_service()
    reply = llm_service.chat([
        {"role": "system", "content": "You are a helpful assistant. Reply in a single world."},
        {"role": "user", "content": "What is the capital of France?"},
    ])
    assert reply.content == "Paris"