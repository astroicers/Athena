# Copyright 2026 Athena Contributors
#
# Use of this software is governed by the Business Source License 1.1
# included in the LICENSE file.
#
# Change Date: Four years from release date of each version
# Change License: Apache License, Version 2.0
#
# For commercial licensing, contact: azz093093.830330@gmail.com

"""Shared LLM client with multi-backend fallback.

Fallback order:
1. Claude API Key (ANTHROPIC_API_KEY / ANTHROPIC_AUTH_TOKEN)
2. Claude OAuth (Claude Code login credentials)
3. OpenAI (OPENAI_API_KEY)
4. Returns empty string (caller decides how to handle)
"""

import logging

import anthropic
import httpx

from app.config import settings, get_task_model_map

logger = logging.getLogger(__name__)

_client: "LLMClient | None" = None


def get_llm_client() -> "LLMClient":
    """Return the singleton LLMClient instance."""
    global _client
    if _client is None:
        _client = LLMClient()
    return _client


class LLMClient:
    """Shared LLM call client supporting multi-backend fallback."""

    def __init__(self) -> None:
        self._anthropic_client: anthropic.AsyncAnthropic | None = None
        self._oauth_manager = None

    def _resolve_backend(self) -> str:
        """Determine which LLM backend to use: api_key, oauth, or none."""
        if settings.LLM_BACKEND != "auto":
            return settings.LLM_BACKEND
        if settings.ANTHROPIC_API_KEY or settings.ANTHROPIC_AUTH_TOKEN:
            return "api_key"
        from app.services.oauth_token_manager import OAuthTokenManager

        if self._oauth_manager is None:
            self._oauth_manager = OAuthTokenManager()
        if self._oauth_manager.is_available():
            return "oauth"
        return "api_key"  # will fall through to OpenAI or empty

    async def call(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        model: str | None = None,
        task_type: str | None = None,
        max_tokens: int = 4000,
        temperature: float = 0.7,
        timeout: float = 60.0,
    ) -> str:
        """Call LLM with multi-backend fallback. Returns raw text response.

        Returns empty string if all backends fail (caller should handle).
        """
        backend = self._resolve_backend()

        if model:
            effective_model = model
        elif task_type:
            effective_model = get_task_model_map().get(task_type)
            if effective_model is None:
                logger.warning("Unknown task_type '%s', falling back to default model %s", task_type, settings.CLAUDE_MODEL)
                effective_model = settings.CLAUDE_MODEL
        else:
            effective_model = settings.CLAUDE_MODEL

        logger.info("LLM call: task_type=%s, model=%s", task_type, effective_model)

        # Try Claude via API Key
        if backend == "api_key" and (
            settings.ANTHROPIC_API_KEY or settings.ANTHROPIC_AUTH_TOKEN
        ):
            try:
                return await self._call_claude(
                    system_prompt, user_prompt, effective_model, max_tokens, temperature, timeout
                )
            except Exception as e:
                logger.warning("Claude API Key failed: %s, trying fallback", e)

        # Try Claude via OAuth
        if backend in ("oauth", "auto"):
            try:
                return await self._call_claude_oauth(
                    system_prompt, user_prompt, effective_model, max_tokens, temperature, timeout
                )
            except Exception as e:
                logger.warning("Claude OAuth failed: %s, trying fallback", e)
                if backend == "oauth" and (
                    settings.ANTHROPIC_API_KEY or settings.ANTHROPIC_AUTH_TOKEN
                ):
                    try:
                        return await self._call_claude(
                            system_prompt, user_prompt, effective_model, max_tokens, temperature, timeout
                        )
                    except Exception as e2:
                        logger.warning("Claude API Key fallback also failed: %s", e2)

        # Fallback to OpenAI
        if settings.OPENAI_API_KEY:
            try:
                return await self._call_openai(
                    system_prompt, user_prompt, max_tokens, temperature, timeout
                )
            except Exception as e:
                logger.warning("OpenAI API failed: %s", e)

        logger.info("No LLM backend available")
        return ""

    async def _call_claude(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str,
        max_tokens: int,
        temperature: float,
        timeout: float,
    ) -> str:
        if self._anthropic_client is None:
            client_kwargs: dict = {"max_retries": 2}
            if settings.ANTHROPIC_API_KEY:
                client_kwargs["api_key"] = settings.ANTHROPIC_API_KEY
            if settings.ANTHROPIC_AUTH_TOKEN:
                client_kwargs["auth_token"] = settings.ANTHROPIC_AUTH_TOKEN
            self._anthropic_client = anthropic.AsyncAnthropic(**client_kwargs)

        message = await self._anthropic_client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
            timeout=timeout,
        )

        if not message.content:
            raise ValueError("Empty content in Claude response")
        return message.content[0].text

    async def _call_claude_oauth(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str,
        max_tokens: int,
        temperature: float,
        timeout: float,
    ) -> str:
        from app.services.oauth_token_manager import OAuthTokenManager, OAUTH_BETA_HEADER

        if self._oauth_manager is None:
            self._oauth_manager = OAuthTokenManager()

        token = await self._oauth_manager.get_access_token()

        client = anthropic.AsyncAnthropic(
            auth_token=token,
            max_retries=2,
            default_headers={"anthropic-beta": OAUTH_BETA_HEADER},
        )

        message = await client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
            timeout=timeout,
        )

        if not message.content:
            raise ValueError("Empty content in Claude OAuth response")
        return message.content[0].text

    async def _call_openai(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int,
        temperature: float,
        timeout: float,
    ) -> str:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.OPENAI_MODEL,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                },
            )
            resp.raise_for_status()
            data = resp.json()
            choices = data.get("choices", [])
            if not choices:
                raise ValueError("Empty choices in OpenAI response")
            return choices[0]["message"]["content"]
