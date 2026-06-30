from src.config import settings
from src.llm.tools import get_tools
from src.llm.history_factory import HistoryFactory
from src.llm.service import LLMService
from src.telegram_bot.group_bot import GroupBot
from openai import OpenAI

def main() -> None:
    client = OpenAI(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
    )

    history_factory = HistoryFactory(
        history_dir=settings.llm_history_dir,
        system_prompt=settings.system_prompt,
    )

    llm_service = LLMService(
        client=client, 
        model=settings.llm_model, 
        tools=get_tools())
    
    bot = GroupBot(
        llm_service, 
        token=settings.telegram_token, 
        bot_username=settings.telegram_bot_username, 
        history_factory=history_factory,
        admin_chat_id=settings.telegram_admin_chat_id,
        admin_question_file=settings.admin_question_file
    )
    bot.run()


if __name__ == "__main__":
    main()