from src.config import Settings
from src.llm.tools import get_tools
from src.llm.history_factory import HistoryFactory
from src.llm.service import LLMService
from src.telegram_bot.admin_reply_handler import AdminReplyHandler
from src.telegram_bot.group_bot import GroupBot
from openai import OpenAI
from langchain_openai import ChatOpenAI
from src.langgraph.app import LangGraphApp
from src.langgraph.nomic_vector_store import NomicVectorStore
class Factory:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def create_llm_service(self) -> LLMService:
        client = OpenAI(
            api_key=self.settings.llm_api_key,
            base_url=self.settings.llm_base_url,
        )
        return LLMService(
            client=client, 
            model=self.settings.llm_model, 
            tools=get_tools()
        )
    
    def create_langgraph_app(self) -> LangGraphApp:
        llm = self.create_chat_openai()
        vector_store = self.create_nomic_vector_store()
        return LangGraphApp(llm=llm, vector_store=vector_store)
    
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
    
    def create_history_factory(self) -> HistoryFactory:
        return HistoryFactory(
            history_dir=self.settings.llm_history_dir,
            system_prompt=self.settings.system_prompt,
        )
    
    def create_admin_reply_handler(self) -> AdminReplyHandler:
        llm_service = self.create_llm_service()
        history_factory = self.create_history_factory()
        return AdminReplyHandler(
            admin_password=self.settings.telegram_admin_password,
            admin_question_file=self.settings.admin_question_file,
            llm_service=llm_service,
            history_factory=history_factory,
        )
    
    def create_group_bot(self) -> GroupBot:
        llm_service = self.create_llm_service()
        history_factory = self.create_history_factory()
        admin_reply_handler = self.create_admin_reply_handler()
        return GroupBot(
            llm_service=llm_service, 
            token=self.settings.telegram_token, 
            bot_username=self.settings.telegram_bot_username, 
            history_factory=history_factory,
            admin_reply_handler=admin_reply_handler,
            langgraph_app=self.create_langgraph_app()
        )
    