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
    
    result = app.format_request_reply(request="Quelle est la date de naissance de Malo Yamakado?", reply="15 mars 1990.")
    print("result", result)
    assert result == "La date de naissance de Malo Yamakado est le 15 mars 1990."