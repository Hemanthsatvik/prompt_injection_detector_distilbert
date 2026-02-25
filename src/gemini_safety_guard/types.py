"""
Type definitions for the Gemini Safety Guard
"""

from dataclasses import dataclass, field
from typing import Literal, Union, TypedDict


# =============================================================================
# Client Configuration
# =============================================================================


@dataclass
class ClientConfig:
    """Configuration for creating a safety agent client."""

    api_key: str | None = None
    """API key for Gemini usage tracking."""


# =============================================================================
# Token Usage
# =============================================================================


@dataclass
class TokenUsage:
    """Token usage information."""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


# =============================================================================
# Message Types
# =============================================================================


class TextContentPart(TypedDict):
    """Text content part for multimodal messages."""

    type: Literal["text"]
    text: str


@dataclass
class ChatMessage:
    """Chat message format for LLM requests."""

    role: Literal["system", "user", "assistant"]
    content: Union[str, list[TextContentPart]]


# =============================================================================
# Guard Types
# =============================================================================


@dataclass
class GuardResponse:
    """Response from guard method including token usage."""

    classification: Literal["pass", "block"]
    """Whether the content passed or should be blocked."""

    reasoning: str
    """Brief explanation of why the content was classified as pass or block."""

    violation_types: list[str]
    """Types of violations detected."""

    cwe_codes: list[str]
    """CWE codes associated with violations."""

    usage: TokenUsage
    """Token usage information."""
