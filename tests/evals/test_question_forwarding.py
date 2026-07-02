from types import SimpleNamespace

import pytest
from src.config import settings
from src.factory.factory import Factory
from telegram import Update
from unittest.mock import AsyncMock, Mock

@pytest.mark.asyncio
async def test_admin_answer_formatting():

    bot = Factory(settings).create_group_bot()
    message = Mock();
    message.text = f"@{bot.bot_username} Quel est la couleur préférée de Malo?"
    message.chat_id = 123
    message.message_id = 456
    message.reply_text = AsyncMock()
    from_user = Mock()
    from_user.id = 42
    from_user.username = "malo"
    from_user.first_name = "Malo"
    message.from_user = from_user


    update = Mock()
    update.update_id = 12345
    update.message = message
    update.effective_chat = SimpleNamespace(id=123)


    context = Mock()
    context.bot = Mock()

    sent_admin_message = Mock()
    sent_admin_message.message_id = 999

    context.bot.send_message = AsyncMock(return_value=sent_admin_message)
    await bot.handle_message(update, context)