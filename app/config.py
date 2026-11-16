"""Runtime configuration read from environment variables (never from source)."""

import os

DEFAULT_MODEL = "gpt-5.4-mini-2026-03-17"

# Spec: transcripts above this many characters return 413.
MAX_TRANSCRIPT_CHARS = 20_000

# Plan: provider call bounded to 22 s, handler work to 25 s, Vercel maxDuration 30 s.
PROVIDER_TIMEOUT_SECONDS = 22.0
HANDLER_DEADLINE_SECONDS = 25.0


def openai_model() -> str:
    return os.environ.get("OPENAI_MODEL", "").strip() or DEFAULT_MODEL


def openai_api_key() -> str | None:
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    return key or None
