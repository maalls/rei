from openai import APIError, OpenAI
import json
import os
from src.llm.history import ConversationHistory

class LLMService:
    def __init__(
        self,
        client: OpenAI,
        model: str,
        history: ConversationHistory,
        tools: list[dict] | None = None

    ):
        self.client = client
        self.model = model
        self.history = history
        self.tools = tools

    def chat(self, user_message: str):

        self.history.add_user(user_message)
                
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=self.history.get_messages(),
                tools=self.tools,
            )

            message = response.choices[0].message
            if message and message.content and message.content != "IDK":
                self.history.add_assistant(message.content)
                self.history.save()

            return message

        except APIError as error:
            print(f"LLM API error: {error}")
            return None