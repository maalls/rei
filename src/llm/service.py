from openai import APIError, OpenAI
import json
import os
from src.llm.history import ConversationHistory

class LLMService:
    def __init__(
        self,
        client: OpenAI,
        model: str,
        tools: list[dict] | None = None

    ):
        self.client = client
        self.model = model
        self.tools = tools

    def chat(self, user_messages: list[dict]) -> dict | None:
                
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=user_messages,
                tools=self.tools,
            )

            message = response.choices[0].message

            return message

        except APIError as error:
            print(f"LLM API error: {error}")
            raise error