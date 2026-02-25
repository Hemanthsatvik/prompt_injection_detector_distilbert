import os
import httpx
from typing import Any
from .types import ChatMessage, TokenUsage
from .schemas import ResponseFormat

class GoogleProvider:
    """Google (Gemini) provider configuration."""

    base_url = "https://generativelanguage.googleapis.com/v1beta/models"
    env_var = "GOOGLE_API_KEY"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ.get(self.env_var)
        if not self.api_key:
            raise ValueError(f"API key is required. Set {self.env_var} env var or pass explicitly.")

    def _transform_messages(self, messages: list[ChatMessage]) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
        """Separate system message from conversation history and format user/model messages."""
        system_instruction: dict[str, Any] | None = None
        contents: list[dict[str, Any]] = []

        system_parts = []
        for msg in messages:
            if msg.role == "system":
                # Assuming simple string content for system, or handle list if needed
                text_content = msg.content if isinstance(msg.content, str) else ""
                system_parts.append({"text": text_content})
            else:
                role = "model" if msg.role == "assistant" else "user"
                # Handle simple string content for now
                parts = [{"text": msg.content}] if isinstance(msg.content, str) else msg.content
                contents.append({
                    "role": role,
                    "parts": parts,
                })
        
        if system_parts:
            system_instruction = {"parts": system_parts}

        return system_instruction, contents

    async def generate_content(
        self,
        model: str,
        messages: list[ChatMessage],
        response_format: ResponseFormat | None = None,
    ) -> tuple[str, TokenUsage]:
        """Call Gemini API."""
        
        system_instruction, contents = self._transform_messages(messages)

        url = f"{self.base_url}/{model}:generateContent?key={self.api_key}"
        
        body: dict[str, Any] = {
            "contents": contents,
        }

        if system_instruction:
            body["systemInstruction"] = system_instruction


        # Add structured output format if provided
        if response_format and response_format.get("type") == "json_schema":
            json_schema = response_format.get("json_schema", {})
            body["generationConfig"] = {
                "responseMimeType": "application/json",
                "responseSchema": json_schema.get("schema"),
            }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers={"Content-Type": "application/json"},
                json=body,
                timeout=30.0
            )

            if response.status_code != 200:
                raise RuntimeError(f"Gemini API Error {response.status_code}: {response.text}")

            data = response.json()
            
            # Extract content
            candidates = data.get("candidates", [])
            content = ""
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                for part in parts:
                    if "text" in part:
                        content += part["text"]
            
            # Extract usage
            usage_meta = data.get("usageMetadata", {})
            usage = TokenUsage(
                prompt_tokens=usage_meta.get("promptTokenCount", 0),
                completion_tokens=usage_meta.get("candidatesTokenCount", 0),
                total_tokens=usage_meta.get("totalTokenCount", 0)
            )

            return content, usage
