from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
import json
import os
from src.langgraph.app import LangGraphApp

class GroupBot:
    def __init__(
            self, 
            token:str, 
            bot_username: str, 
            admin_password: str,
            langgraph_app: LangGraphApp
        ) -> None:       
        
        self.token = token
        self.bot_username = bot_username
        self.admin_password = admin_password
        self.langgraph_app = langgraph_app


    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_text("Hello!")

    async def claim_admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        
        password = context.args[0] if context.args else None
        if password == self.admin_password:
            
            # store the admin chat ID in a file for persistence
            id_file_path = "var/admin_chat_id.txt"
            chat_id = update.effective_chat.id
            os.makedirs(os.path.dirname(id_file_path), exist_ok=True)
            with open(id_file_path, "w") as f:
                f.write(str(chat_id))
            self.admin_chat_id = chat_id
            await update.message.reply_text("Chat admin set.")
        else:
            await update.message.reply_text("Incorrect password.")


    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT) -> None:
        if not update.message or not update.message.text:
            return
        
        message = self.format_message(update)
        
        response = await self.langgraph_app.invoke(message)
        print("replying", response)
        if(response):
            await update.message.reply_text(response)

    def format_message(self, update: Update) -> dict:
        message = update.effective_message
        user = update.effective_user
        chat = update.effective_chat

        mentions = []

        if message.entities:
            for entity in message.entities:
                if entity.type == "mention":
                    mentions.append(
                        message.text[
                            entity.offset : entity.offset + entity.length
                        ]
                    )

        return {
            "source": "telegram",
            "chat_type": chat.type,
            "chat_id": chat.id,
            "message_id": message.message_id,
            "from": {
                "user_id": user.id,
                "username": (
                    f"@{user.username}"
                    if user.username
                    else None
                ),
                "display_name": user.full_name,
            },
            "text": message.text,
            "mentions": mentions,
            "reply_to": (
                {
                    "message_id": message.reply_to_message.message_id,
                    "user_id": message.reply_to_message.from_user.id,
                    "username": (
                        f"@{message.reply_to_message.from_user.username}"
                        if message.reply_to_message.from_user.username
                        else None
                    ),
                }
                if message.reply_to_message
                else None
            ),
        }
    

    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        print(f"An error occurred: {context.error}")
        # send a message to the user if possible
        if update and isinstance(update, Update) and update.message:
            try:
                await update.message.reply_text(f"An error occurred while processing your request. Please try again later. ({context.error})")
                raise context.error
            except Exception as e:
                print(f"Failed to send error message to user: {e}")
                raise e

    def run(self) -> None:
        print("Starting bot")
        application = ApplicationBuilder().token(self.token).build()
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("claim", self.claim_admin_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        application.add_error_handler(self.error_handler)
        print("Polling...")
        application.run_polling(poll_interval=1.0)