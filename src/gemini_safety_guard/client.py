import asyncio
import json
import os
from typing import Any

from .types import (
    GuardResponse,
    TokenUsage,
    ChatMessage,
)
from .schemas import GUARD_RESPONSE_FORMAT
from .provider import GoogleProvider
from .prompts import build_guard_user_message, build_guard_system_prompt
from .utils import chunk_text

# Default Gemini model
DEFAULT_GUARD_MODEL = "gemini-flash-latest"

class SafetyClient:
    """
    Safety Agent Client powered by Gemini.
    """

    def __init__(self, api_key: str | None = None):
        """
        Initialize the Safety Agent client.

        Args:
            api_key: Optional API key (defaults to GOOGLE_API_KEY env var)
        """
        self.provider = GoogleProvider(api_key=api_key)

    async def _guard_single_text(
        self,
        input_text: str,
        system_prompt: str | None,
        model: str,
    ) -> GuardResponse:
        """Guard a single chunk of text input (internal method)."""
        
        final_system_prompt = build_guard_system_prompt(system_prompt)
        
        messages: list[ChatMessage] = [
            ChatMessage(role="system", content=final_system_prompt),
            ChatMessage(role="user", content=build_guard_user_message(input_text))
        ]

        content, usage = await self.provider.generate_content(
            model=model,
            messages=messages,
            response_format=GUARD_RESPONSE_FORMAT
        )

        try:
            parsed = json.loads(content)
            return GuardResponse(
                classification=parsed.get("classification", "pass"),
                reasoning=parsed.get("reasoning", ""),
                violation_types=parsed.get("violation_types", []),
                cwe_codes=parsed.get("cwe_codes", []),
                usage=usage,
            )
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse guard response: {content}") from e

    def _aggregate_guard_results(self, results: list[GuardResponse]) -> GuardResponse:
        """
        Aggregate multiple guard results using OR logic.
        Block if ANY chunk is blocked, merge all violations.
        """
        has_block = any(r.classification == "block" for r in results)

        # Merge and deduplicate violation types and CWE codes
        all_violations: set[str] = set()
        all_cwe_codes: set[str] = set()

        for r in results:
            all_violations.update(r.violation_types)
            all_cwe_codes.update(r.cwe_codes)

        # Collect reasoning from blocked results, or from first result if all pass
        blocked_results = [r for r in results if r.classification == "block"]
        if blocked_results:
            reasoning = " ".join(r.reasoning for r in blocked_results)
        else:
            reasoning = results[0].reasoning if results else ""

        return GuardResponse(
            classification="block" if has_block else "pass",
            reasoning=reasoning,
            violation_types=list(all_violations),
            cwe_codes=list(all_cwe_codes),
            usage=TokenUsage(
                prompt_tokens=sum(r.usage.prompt_tokens for r in results),
                completion_tokens=sum(r.usage.completion_tokens for r in results),
                total_tokens=sum(r.usage.total_tokens for r in results),
            ),
        )

    async def guard(
        self,
        input: str,
        *,
        model: str = DEFAULT_GUARD_MODEL,
        system_prompt: str | None = None,
        chunk_size: int = 8000,
    ) -> GuardResponse:
        """
        Guard method - Classifies input as pass/block.

        Args:
            input: The input text to analyze
            model: Gemini model to use. Default: gemini-1.5-flash
            system_prompt: Optional custom system prompt
            chunk_size: Characters per chunk. Default: 8000. Set to 0 to disable chunking.

        Returns:
            Response with classification result and token usage
        """
        # Skip chunking if disabled (chunk_size=0) or input is small enough
        if chunk_size == 0 or len(input) <= chunk_size:
            return await self._guard_single_text(input, system_prompt, model)

        # Chunk and process in parallel
        chunks = chunk_text(input, chunk_size)
        results = await asyncio.gather(
            *[
                self._guard_single_text(chunk, system_prompt, model)
                for chunk in chunks
            ]
        )

        return self._aggregate_guard_results(list(results))


def create_client(api_key: str | None = None) -> SafetyClient:
    """Create a new Safety Agent client."""
    return SafetyClient(api_key=api_key)


class LocalSafetyClient:
    """
    Safety client powered by a local DistilBert model.
    Provides the same guard() interface as SafetyClient.
    """

    def __init__(self, model_path: str | None = None):
        """
        Initialize the local safety client.

        Args:
            model_path: Path to the local DistilBert model directory.
        """
        from .local_model import LocalModelProvider
        self.provider = LocalModelProvider(model_path=model_path)

    async def guard(
        self,
        input: str,
        **kwargs,
    ) -> "GuardResponse":
        """
        Guard method - Classifies input as pass/block using the local model.

        Args:
            input: The input text to analyze

        Returns:
            GuardResponse with classification result
        """
        return self.provider.predict(input)


def create_local_client(model_path: str | None = None) -> LocalSafetyClient:
    """Create a new local Safety Agent client using the DistilBert model."""
    return LocalSafetyClient(model_path=model_path)
