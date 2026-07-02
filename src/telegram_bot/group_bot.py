from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from src.llm.history_factory import HistoryFactory
from src.llm.service import LLMService
from src.telegram_bot.admin_reply_handler import AdminReplyHandler
import json
import os


class GroupBot:
    def __init__(
            self, 
            llm_service: LLMService, 
            token:str, 
            bot_username: str, 
            history_factory: HistoryFactory,
            admin_reply_handler: AdminReplyHandler,
            
            
        ) -> None:       
        self.llm_service = llm_service
        self.token = token
        self.bot_username = bot_username
        self.admin_reply_handler = admin_reply_handler
        self.history_factory = history_factory

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_text("Hello!")

    async def claim_admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        
        password = context.args[0] if context.args else None
        if password == self.admin_reply_handler.admin_password:
            self.admin_reply_handler.store_admin_chat_id(update.effective_chat.id)
            await update.message.reply_text("Chat admin set.")
        else:
            await update.message.reply_text("Incorrect password.")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message or not update.message.text:
            return
        
        if await self.admin_reply_handler.handle_admin_reply(update, context):
            return
        
        print(json.dumps(update.message.to_dict(), default=str, indent=2))
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

        history = self.history_factory.for_channel(update.effective_chat.id)
        history.add_user(user_message)
        

        while True:
            print("looping over LLM...")
            
            messages = history.get_messages()
            print("last message in history:", messages[-1] if messages else "No messages in history")
            message = self.llm_service.chat(messages)


            if message.tool_calls:
                print(f"Tool calls received: {message.tool_calls}")
                history.add_message(message.model_dump())
                for tool_call in message.tool_calls:
                    arguments = json.loads(tool_call.function.arguments)
                    
                    if tool_call.function.name == "aiaiai":
                        print("Tool call: aiaiai")
                        content = "Ai Ai Ai!"
                    elif tool_call.function.name == "calendar_availability":

                        print("Tool call: calendar_availability", arguments)
                        
                        person = arguments.get("person")
                        date = arguments.get("date")
                        start_time = arguments.get("start_time")
                        duration = arguments.get("duration")
                        print(f"Tool call: calendar_availability for {person} on {date} starting at {start_time} for {duration}")
                        content =  f"Checked calendar availability for {person} on {date} starting at {start_time} for {duration}."
                        
                    elif tool_call.function.name == "profile":
                        arguments = json.loads(tool_call.function.arguments)
                        print("Tool call: profile", arguments)
                        person = arguments.get("person")
                        label = arguments.get("label")
                        details = arguments.get("details")
                        print(f"Tool call: profile for {person}, {label}: {details}")
                        # Here you would implement the logic to get the profile information
                        # For now, we will just send a placeholder response
                        content = f"Retrieved profile information for {person}: {{}}"
                    
                    elif tool_call.function.name == "transmit_request":
                        await self.admin_reply_handler.notify_admin(update, context, arguments.get("details"))
                        content = {
                        "status": "sent_to_admin",
                        "admin_has_replied_status": "pending_for_admin_reply",
                        "instruction": "the question has been sent to the admin. The admin will reply when they have an answer. The user will be notified later when the admin replies.",
                    }
                    else:
                        raise ValueError(f"Unknown tool call: {tool_call.function.name}")   
                    
                    tool_message = {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps({"result": content}),
                    }
                    history.add_message(tool_message)

            elif message.content:
                print(f"Sending response: {message.content}\n end of response")
                history.add_assistant(message.content)
                await update.message.reply_text(message.content)
                return
            else:
                error = "error: No content or tool calls received from LLM service. Ending loop."
                print(error)
                await update.message.reply_text(error)
                return

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
        application.add_handler(CommandHandler("claim_admin", self.claim_admin_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        application.add_error_handler(self.error_handler)
        print("Polling...")
        application.run_polling(poll_interval=1.0)