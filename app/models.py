"""Public API request/response models."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Tier = Literal["Hot", "Warm", "Cold"]
Routing = Literal["kam_handoff", "nurture_pool", "auto_archive"]


class Message(BaseModel):
    # Unknown extra keys are ignored; role and text are required.
    role: Literal["lead", "agent"]
    text: str = Field(min_length=1)


class ScoreRequest(BaseModel):
    # Extra top-level keys (for example a country field) are accepted and ignored:
    # channel and country never change scoring weights.
    lead_id: str = Field(min_length=1)
    channel: str
    conversation: list[Message] = Field(min_length=1)

    def transcript_chars(self) -> int:
        return sum(len(m.text) for m in self.conversation)


class ScoreResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lead_id: str
    score: int = Field(ge=0, le=100)
    tier: Tier
    routing: Routing
    reasoning: str = Field(min_length=1)


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail
    request_id: str
