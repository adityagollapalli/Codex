"""Optional LLM integration for richer summarization and answer synthesis."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings


@dataclass(slots=True)
class LLMResult:
    """Represents a generated text response."""

    content: str


class NullLLMProvider:
    """No-op provider used when external LLM access is unavailable."""

    available = False

    def summarize(self, text: str) -> LLMResult | None:
        return None

    def answer(self, question: str, context: str) -> LLMResult | None:
        return None


class OpenAIProvider:
    """Small OpenAI wrapper kept optional via environment variables."""

    available = True

    def __init__(self, api_key: str, model: str) -> None:
        from openai import OpenAI

        self.client = OpenAI(api_key=api_key)
        self.model = model

    def summarize(self, text: str) -> LLMResult | None:
        prompt = (
            "Summarize the following document in a concise, factual paragraph. "
            "Do not invent information.\n\n"
            f"{text[:12000]}"
        )
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You create grounded document summaries."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )
        content = completion.choices[0].message.content or ""
        return LLMResult(content=content.strip())

    def answer(self, question: str, context: str) -> LLMResult | None:
        prompt = (
            "Answer the question using only the provided context. "
            "If the context is insufficient, explicitly say so.\n\n"
            f"Question: {question}\n\n"
            f"Context:\n{context[:12000]}"
        )
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You answer questions with grounded evidence only."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
        )
        content = completion.choices[0].message.content or ""
        return LLMResult(content=content.strip())


def build_llm_provider(settings: Settings) -> NullLLMProvider | OpenAIProvider:
    """Return the configured LLM provider or a safe no-op fallback."""

    if not settings.openai_api_key:
        return NullLLMProvider()

    try:
        return OpenAIProvider(api_key=settings.openai_api_key, model=settings.openai_model)
    except Exception:
        return NullLLMProvider()
