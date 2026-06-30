from src.config import settings
from src.llm.tools import get_tools
from src.llm.history import ConversationHistory
from src.llm.service import LLMService
from src.telegram_bot.bot import TelegramBot
from openai import OpenAI

def main() -> None:
    client = OpenAI(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
    )

    history = ConversationHistory(
        history_file=settings.llm_history_file,
        system_prompt=settings.system_prompt,
    )

    llm_service = LLMService(
        client=client, 
        model=settings.llm_model, 
        history=history, 
        tools=get_tools())
    
    bot = TelegramBot(
        llm_service, 
        token=settings.telegram_token, 
        bot_username=settings.telegram_bot_username, 
        admin_chat_id=settings.telegram_admin_chat_id,
        admin_question_file=settings.admin_question_file
    )
    bot.run()


if __name__ == "__main__":
    main()