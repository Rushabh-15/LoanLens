import os

from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

if not ANTHROPIC_API_KEY:
    raise ValueError(
        "ANTHROPIC_API_KEY is not set. "
        "Check your .env file and ensure load_dotenv() is working."
    )

CLAUDE_MODEL = os.getenv(
    "CLAUDE_MODEL",
    "claude-haiku-4-5-20251001"
)

MAX_TOKENS = 2048

TEMPERATURE = 0