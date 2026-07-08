from src.config import Settings
from telegram import Bot

from src.telegram_bot.group_bot import GroupBot
from langchain_openai import ChatOpenAI
from src.langgraph.app import LangGraphApp
from src.langgraph.nomic_vector_store import NomicVectorStore
from src.telegram_bot.admin_bot import AdminBot
class Factory:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def create_langgraph_app(self) -> LangGraphApp:
        llm = self.create_chat_openai()
        vector_store = self.create_nomic_vector_store()
        admin_bot = AdminBot(Bot(token=self.settings.telegram_token), username=self.settings.telegram_bot_username, 
            admin_password=self.settings.telegram_admin_password)
        return LangGraphApp(llm=llm, vector_store=vector_store, admin_bot=admin_bot)
    
    def create_nomic_vector_store(self) -> NomicVectorStore:
        return NomicVectorStore(
            model=self.settings.llm_model,
            base_url=self.settings.llm_base_url,
            api_key=self.settings.llm_api_key,
        )

    def create_chat_openai(self) -> ChatOpenAI:
        return ChatOpenAI(
            model_name=self.settings.llm_model,
            openai_api_key=self.settings.llm_api_key,
            openai_api_base=self.settings.llm_base_url,
            temperature=0
        )
    
    def create_group_bot(self) -> GroupBot:
        
        return GroupBot(
            token=self.settings.telegram_token, 
            bot_username=self.settings.telegram_bot_username, 
            admin_password=self.settings.telegram_admin_password,
            langgraph_app=self.create_langgraph_app()
        )
    