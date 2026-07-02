# src/telegram_bot/admin_reply_handler.py

import json
import os
from telegram import Update
from telegram.ext import ContextTypes

from src.llm.history_factory import HistoryFactory
from src.llm.service import LLMService


class AdminReplyHandler:
    def __init__(
        self,
        admin_password: str,
        admin_question_file: str,
        llm_service: LLMService,
        history_factory: HistoryFactory,
    ) -> None:
        self.admin_password = admin_password
        self.init_admin_chat_id()
        self.admin_question_file = admin_question_file
        self.llm_service = llm_service
        self.history_factory = history_factory

    def init_admin_chat_id(self) -> None:
        id_file_path = "var/admin_chat_id.txt"
        if os.path.exists(id_file_path):
            with open(id_file_path, "r") as f:
                self.admin_chat_id = int(f.read().strip())
        else:
            self.admin_chat_id = None

    def store_admin_chat_id(self, chat_id: int) -> None:
        # store the admin chat ID in a file for persistence
        id_file_path = "var/admin_chat_id.txt"
        os.makedirs(os.path.dirname(id_file_path), exist_ok=True)
        with open(id_file_path, "w") as f:
            f.write(str(chat_id))
        self.admin_chat_id = chat_id

    async def notify_admin(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        question: str,
    ) -> None:
        if not self.admin_chat_id:
            await update.message.reply_text(
                "Je ne suis pas sûr de la réponse. Et je n’ai pas pu contacter l'administrateur car le chat admin ID n'est pas défini."
            )
            return

        user = update.message.from_user
        username = user.username or user.full_name or str(user.id)

        print("Notifying admin with question:", question)
        text = f"Question de la part de {username} pour toi :\n\n{question}"
        self.history_factory.for_channel(self.admin_chat_id).add_assistant(text)
        admin_message = await context.bot.send_message(
            chat_id=self.admin_chat_id,
            text=text,
        )

        self._append_pending_question(
            {
                "admin_message_id": admin_message.message_id,
                "question": question,
                "user_id": user.id,
                "chat_id": update.effective_chat.id,
                "user_message_id": update.message.message_id,
            }
        )

    async def handle_admin_reply(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ) -> bool:
        if not self._is_admin_reply(update):
            return False

        replied_message_id = update.message.reply_to_message.message_id
        pending_questions = self._load_pending_questions()

        for pending_question in pending_questions:
            if pending_question["admin_message_id"] != replied_message_id:
                continue

            answer = update.message.text
            self.history_factory.for_channel(self.admin_chat_id).add_user(answer)

            final_answer = self._format_admin_answer(
                question=pending_question["question"],
                answer=answer,
            )

            user_chat_id = pending_question["chat_id"]
            user_message_id = pending_question["user_message_id"]

            history = self.history_factory.for_channel(user_chat_id)
            
            history.add_assistant(final_answer)

            await context.bot.send_message(
                chat_id=user_chat_id,
                text=final_answer,
                reply_to_message_id=user_message_id,
            )

            pending_questions.remove(pending_question)
            self._save_pending_questions(pending_questions)

            await update.message.reply_text("Réponse transmise:\n" + final_answer)
            return True

        return False

    def _format_admin_answer(self, question: str, answer: str) -> str:
        message = {
            "role": "user",
            "content": (
                "Reformulate the answer so it is clear and concise. If it's in the first person, reformulate it to be in the third person.\n"
                f"Question: {question}\n"
                f"Answer: {answer}\n\n"
                "You must reformulate the answer in the same language as the original question."
            ),
        }

        response = self.llm_service.chat([message])
        print(f"Admin's answer: {answer}")
        print(f"Formatted answer:", response)
        return response.content or answer

    def _is_admin_reply(self, update: Update) -> bool:
        if not self.admin_chat_id or not self.admin_question_file:
            return False

        if not update.effective_chat:
            return False

        if update.effective_chat.id != int(self.admin_chat_id):
            return False

        if not update.message or not update.message.text:
            return False

        if not update.message.reply_to_message:
            return False

        return True

    def _append_pending_question(self, pending_question: dict) -> None:
        if not self.admin_question_file:
            return

        with open(self.admin_question_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(pending_question, ensure_ascii=False) + "\n")

    def _load_pending_questions(self) -> list[dict]:
        if not self.admin_question_file:
            return []

        if not os.path.exists(self.admin_question_file):
            return []

        with open(self.admin_question_file, "r", encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]

    def _save_pending_questions(self, pending_questions: list[dict]) -> None:
        if not self.admin_question_file:
            return

        with open(self.admin_question_file, "w", encoding="utf-8") as f:
            for question in pending_questions:
                f.write(json.dumps(question, ensure_ascii=False) + "\n")