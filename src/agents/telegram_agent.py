# Design to communicate with other agent (human or not)
from telegram import Bot

class TelegramAgent:

    def __init__(self, bot: Bot, username: str, chat_id: str):
        self.bot = bot
        self.username = username
        self.chat_id = chat_id

    async def send_message(self, message: str):

        return await self.bot.send_message(
            chat_id=self.chat_id,
            text=message
        )