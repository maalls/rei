from src.llm.history import ConversationHistory


class HistoryFactory:
    def __init__(
        self,
        history_dir: str,
        system_prompt: str | None = None,
    ):
        self.history_dir = history_dir
        self.system_prompt = system_prompt

    def for_channel(self, channel_id: int | str) -> ConversationHistory:
        return ConversationHistory(
            history_file=f"{self.history_dir}/chat_{channel_id}.json",
            system_prompt=self.system_prompt,
        )