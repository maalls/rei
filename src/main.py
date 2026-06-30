from src.config import settings
from src.llm.service import LLMService
from src.telegram_bot.bot import TelegramBot
from openai import OpenAI

def main() -> None:
    client = OpenAI(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
    )

    llm_service = LLMService(client=client, model=settings.llm_model, system_prompt=settings.system_prompt, history_file=settings.llm_history_file)
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