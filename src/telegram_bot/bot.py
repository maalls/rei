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
import os

class TelegramBot:
    def __init__(
            self, 
            llm_service: LLMService, 
            token:str, 
            bot_username: str, 
            admin_chat_id: str | None = None,
            admin_question_file: str | None = None
        ) -> None:       
        self.llm_service = llm_service
        self.token = token
        self.bot_username = bot_username
        self.admin_chat_id = admin_chat_id
        self.admin_question_file = admin_question_file

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_text("Hello!")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message or not update.message.text:
            return
        
        if await self.handle_admin_reply(update, context):
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
                if tool_call.function.name == "aiaiai":
                    print("Tool call: aiaiai")
                    self.llm_service.history.add_assistant("Ai Ai Ai!")
                    self.llm_service.history.save()
                    await update.message.reply_text("Ai Ai Ai!")

        if message.content:

            if message.content == "IDK":
                await self.notify_admin(update, context, user_message)
            else:
                print(f"Sending response: {message.content}")
                await update.message.reply_text(message.content)


    async def notify_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE, question: str) -> None:
        if self.admin_chat_id:

            user = update.message.from_user
            username = (
                user.username
                or user.full_name
                or str(user.id)
            )
            admin_message = await context.bot.send_message(
                chat_id=self.admin_chat_id,
                text=f"Question de la part de {username} pour toi :\n\n{question}",
            )
            await update.message.reply_text(
                "Je ne suis pas sûr de la réponse. Je lui ai transmis ta question et je reviens vers toi."
            )
            
            pending_question = {
                "admin_message_id": admin_message.message_id,
                "question": question,
                "user_id": update.message.from_user.id,
                "chat_id": update.effective_chat.id,
                "user_message_id": update.message.message_id,
            }
            if self.admin_question_file:
                if not os.path.exists(self.admin_question_file):
                    open(self.admin_question_file, "w").close()
                try:
                    with open(self.admin_question_file, "a") as f:
                        f.write(json.dumps(pending_question) + "\n")
                except Exception as e:
                    print(f"Failed to write pending question to file: {e}")
        else:
            await update.message.reply_text(
                            "Je ne suis pas sûr de la réponse. Mais je n’ai pas pu contacter Malo."
            )

    async def handle_admin_reply(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        if not self.admin_chat_id or not self.admin_question_file:
            return False

        if update.effective_chat.id != int(self.admin_chat_id):
            return False

        if not update.message or not update.message.reply_to_message:
            return False

        replied_message_id = update.message.reply_to_message.message_id
        try:
            with open(self.admin_question_file, "r") as f:
                pending_questions = [json.loads(line) for line in f]
        except FileNotFoundError:
            print("Admin question file not found.")
            return False

        for pending_question in pending_questions:
            if pending_question["admin_message_id"] == replied_message_id:
                user_chat_id = pending_question["chat_id"]
                user_message_id = pending_question["user_message_id"]
                answer = update.message.text

                await context.bot.send_message(
                    chat_id=user_chat_id,
                    text=f"Réponse de Malo :\n\n{answer}",
                    reply_to_message_id=user_message_id,
                )

                # Remove the answered question from the file
                pending_questions.remove(pending_question)
                with open(self.admin_question_file, "w") as f:
                    for question in pending_questions:
                        f.write(json.dumps(question) + "\n")
                return True

        return False
       

    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        print(f"An error occurred: {context.error}")
        # send a message to the user if possible
        if update and isinstance(update, Update) and update.message:
            try:
                await update.message.reply_text("An error occurred while processing your request. Please try again later.")
            except Exception as e:
                print(f"Failed to send error message to user: {e}")

    def run(self) -> None:
        print("Starting bot")
        application = ApplicationBuilder().token(self.token).build()
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        application.add_error_handler(self.error_handler)
        print("Polling...")
        application.run_polling(poll_interval=1.0)