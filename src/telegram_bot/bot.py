from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from src.llm.service import LLMService
import json

class TelegramBot:
    def __init__(self, llm_service: LLMService, token:str, bot_username: str, admin_chat_id: str | None = None):       
        self.llm_service = llm_service
        self.token = token
        self.bot_username = bot_username
        self.admin_chat_id = admin_chat_id

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_text("Hello! I'm your bot. How can I assist you today?")

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_text("Send me a message and I will answer using the configured LLM.")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message or not update.message.text:
            return
        
        print(f"Received message: {update.message.text} from user: {update.message.from_user.username}")
        print("chat_id:", update.effective_chat.id)
        message_type = update.message.chat.type
        user_message = update.message.text

        if message_type in ["group", "supergroup"]:
            mention = f"@{self.bot_username}"

            print(f"Received message: {user_message} from chat type: {message_type}")

            if mention not in user_message:
                print(f"Bot {self.bot_username} was not mentioned in the group message. Ignoring.")
                return

            user_message = user_message.replace(mention, "").strip()

        message = self.llm_service.chat(user_message)

        if message.tool_calls:
            print(f"Tool calls received: {message.tool_calls}")
            for tool_call in message.tool_calls:
                if tool_call.function.name == "ask_human":
                    print("tool", json.dumps(tool_call.model_dump(), indent=2))
                    arguments = json.loads(tool_call.function.arguments)
                    question = arguments.get("question", "")
                    print(f"Tool call: ask_human\nQuestion: {question}")
                    await self.notify_admin(update, context, question)
                    
                elif tool_call.function.name == "aiaiai":
                    print("Tool call: aiaiai")
                    await update.message.reply_text("Ai Ai Ai!")

        
        if message.content:

            if message.content == "IDK":
                await self.notify_admin(update, context, user_message)
            else:
                print(f"Sending response: {message.content}")
                await update.message.reply_text(message.content)


    async def notify_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE, question: str) -> None:
        if self.admin_chat_id:
            await context.bot.send_message(
                chat_id=self.admin_chat_id,
                text=f"❓ Question pour Malo :\n\n{question}",
            )
            await update.message.reply_text(
                            "Je ne suis pas sûr de la réponse. J’ai transmis ta question à Malo."
                        )
        else:
            await update.message.reply_text(
                            "Je ne suis pas sûr de la réponse. Mais je n’ai pas pu contacter Malo."
            )
       

    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        print(f"An error occurred: {context.error}")
        # send a message to the user if possible
        if update and isinstance(update, Update) and update.message:
            try:
                await update.message.reply_text("An error occurred while processing your request. Please try again later.")
            except Exception as e:
                print(f"Failed to send error message to user: {e}")

    def run(self) -> None:
        application = ApplicationBuilder().token(self.token).build()
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        application.add_error_handler(self.error_handler)

        print("Polling...")
        application.run_polling(poll_interval=1.0)