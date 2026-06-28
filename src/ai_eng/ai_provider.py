"""Pluggable AI provider abstraction.

The whole point of this prototype is "AI assists the engineer within tasks; the
engineer owns execution and quality". To make that concrete *and* reproducible,
AI access is hidden behind a small interface with two implementations:

* :class:`OfflineProvider` (default) - deterministic, no network, no API key.
  It returns structured, reviewable suggestions so the pipeline runs anywhere
  (CI, an interview laptop, an air-gapped box) and produces identical output.

* :class:`OpenAIProvider` - a thin adapter over a real LLM, enabled only when an
  API key is configured. It demonstrates the *integration point*; it is never
  required to run the demo.

This separation is itself an engineering decision: AI is a swappable accelerator,
not a hard dependency, and its output is always mediated by our own code.
"""

from __future__ import annotations

import os
from typing import Protocol


class AIProvider(Protocol):
    """Minimal surface every provider must implement."""

    name: str

    def complete(self, prompt: str, *, system: str = "") -> str:
        """Return a completion for ``prompt``."""
        ...


class OfflineProvider:
    """Deterministic, dependency-free provider.

    It does not attempt to *be* a model. Instead it echoes the prompt back in a
    structured, auditable way so the pipeline is fully reproducible and the
    "where did AI help?" question always has a concrete, inspectable answer.
    """

    name = "offline-deterministic"

    def complete(self, prompt: str, *, system: str = "") -> str:
        header = "[offline-ai-suggestion]"
        sys_line = f"context: {system}" if system else "context: (none)"
        return f"{header}\n{sys_line}\nprompt:\n{prompt.strip()}"


class OpenAIProvider:
    """Adapter for a live OpenAI-compatible endpoint.

    Reads configuration from the environment so no secrets live in code:

    * ``OPENAI_API_KEY`` - required
    * ``OPENAI_BASE_URL`` - optional (supports proxies / self-hosted gateways)
    * ``OPENAI_MODEL``    - optional, defaults to ``gpt-4o-mini``
    """

    name = "openai"

    def __init__(self, model: str | None = None) -> None:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is not set; use OfflineProvider for offline runs."
            )
        try:
            from openai import OpenAI  # imported lazily so it stays optional
        except ImportError as exc:  # pragma: no cover - exercised only with extra
            raise RuntimeError(
                "The 'openai' package is not installed. Install with "
                "'pip install .[ai]' to use the live provider."
            ) from exc

        base_url = os.environ.get("OPENAI_BASE_URL")
        self._client = OpenAI(api_key=api_key, base_url=base_url)
        self._model = model or os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    def complete(self, prompt: str, *, system: str = "") -> str:  # pragma: no cover
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        response = self._client.chat.completions.create(
            model=self._model, messages=messages, temperature=0.2
        )
        return response.choices[0].message.content or ""


def default_provider() -> AIProvider:
    """Choose a provider based on the environment.

    Live AI is opt-in: it is used only when ``OPENAI_API_KEY`` is present *and*
    ``AI_ENG_PROVIDER`` is not pinned to ``offline``. Otherwise we stay offline
    so behaviour is reproducible by default.
    """

    pinned = os.environ.get("AI_ENG_PROVIDER", "").lower()
    if pinned == "offline":
        return OfflineProvider()
    if pinned == "openai" or os.environ.get("OPENAI_API_KEY"):
        try:
            return OpenAIProvider()
        except RuntimeError:
            return OfflineProvider()
    return OfflineProvider()
