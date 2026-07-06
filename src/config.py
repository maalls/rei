from dataclasses import dataclass
from pathlib import Path
import os

from dotenv import load_dotenv

load_dotenv(override=True)


def normalize_base_url(raw_base_url: str | None) -> str:
    if not raw_base_url:
        raise ValueError("URL is not set.")

    base_url = raw_base_url.rstrip("/")
    if not base_url.endswith("/v1"):
        base_url = f"{base_url}/v1"

    return base_url


def load_system_prompt() -> str:
    prompt_path = Path("prompts/system.md")

    if not prompt_path.exists():
        prompt_path = Path("prompts/system.default.md")

    return prompt_path.read_text(encoding="utf-8")


@dataclass(frozen=True)
class Settings:
    telegram_token: str
    telegram_bot_username: str
    telegram_admin_password: str
    llm_api_key: str
    llm_base_url: str
    llm_model: str
    system_prompt: str
    llm_history_dir: str | None = None
    admin_question_file: str | None = None
    embeddings_model: str | None = None
    embeddings_base_url: str | None = None
    embeddings_api_key: str | None = None
    

print(os.getenv("EMBEDDINGS_MODEL"))

settings = Settings(
    telegram_token=os.environ["TELEGRAM_TOKEN"],
    telegram_bot_username=os.environ["TELEGRAM_BOT_USERNAME"],
    telegram_admin_password=os.environ["TELEGRAM_ADMIN_PASSWORD"],
    llm_api_key=os.getenv("LLM_API_KEY", "dummy_key") or "dummy_key",
    llm_base_url=normalize_base_url(os.getenv("LLM_BASE_URL")),
    llm_model=os.environ["LLM_MODEL"],
    system_prompt=load_system_prompt(),
    llm_history_dir=os.getenv("LLM_HISTORY_DIR") or "var/llm_history",
    admin_question_file=os.getenv("ADMIN_QUESTION_FILE") or "var/admin_questions.json",
    embeddings_model=os.getenv("EMBEDDINGS_MODEL"),
    embeddings_base_url=normalize_base_url(os.getenv("EMBEDDINGS_BASE_URL")),
    embeddings_api_key=os.getenv("EMBEDDINGS_API_KEY"),
)