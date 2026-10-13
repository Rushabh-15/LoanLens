import os
from dataclasses import dataclass, field
from functools import lru_cache

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    anthropic_api_key: str | None = field(repr=False)
    claude_model: str
    database_url: str
    max_tokens: int


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Read configuration on first call and cache the result."""
    load_dotenv()

    return Settings(
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY") or None,
        claude_model=os.getenv(
            "CLAUDE_MODEL",
            "claude-haiku-5-5",
        ),
        database_url=os.getenv(
            "DATABASE_URL",
            "sqlite:///loanlens.db",
        ),
        max_tokens=int(os.getenv("MAX_TOKENS", "2048")),
    )