# src/llm/history.py

import json
from pathlib import Path


class ConversationHistory:
    def __init__(self, history_file: str | None, system_prompt: str | None = None):
        self.history_file = Path(history_file) if history_file else None
        self.system_prompt = system_prompt
        self.messages: list[dict] = self._load()

    def _load(self) -> list[dict]:
        if not self.history_file or not self.history_file.exists():
            return self._initial_messages()

        with self.history_file.open("r", encoding="utf-8") as f:
            messages = json.load(f)

        return messages or self._initial_messages()

    def _initial_messages(self) -> list[dict]:
        if not self.system_prompt:
            return []

        return [{"role": "system", "content": self.system_prompt}]

    def add_user(self, content: str) -> None:
        self.messages.append({"role": "user", "content": content})
        self.save()

    def add_message(self, message: dict) -> None:
        self.messages.append(message)
        self.save()

    def add_assistant_message(self, message) -> None:
        item = {"role": "assistant", "content": message.content}
        if message.tool_calls:
            item["tool_calls"] = [
                tool_call
                for tool_call in message.tool_calls
            ]
            self.messages.append(item)
            self.save()

    def add_assistant(self, content) -> None:
        self.messages.append({"role": "assistant", "content": content})
        self.save()
    
    def add_tool(self, tool_call_id: str, content: str) -> None:
        self.messages.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": content,
        })
        self.save()

    def add_system(self, content: str) -> None:
        self.messages.append({"role": "system", "content": content})
        self.save()

    def get_messages(self) -> list[dict]:
        return self.messages

    def save(self) -> None:
        if not self.history_file:
            return

        self.history_file.parent.mkdir(parents=True, exist_ok=True)

        with self.history_file.open("w", encoding="utf-8") as f:
            json.dump(self.messages, f, indent=2, ensure_ascii=False)

    