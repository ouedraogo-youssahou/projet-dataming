import logging
from typing import Any, Dict, Optional

import openai
from anthropic import Anthropic

logger = logging.getLogger(__name__)


class LLMWrapper:
    """Unified wrapper for OpenAI and Anthropic LLMs."""

    def __init__(
        self,
        openai_key: Optional[str] = None,
        anthropic_key: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        self.config = config or {}
        self.openai_key = openai_key or self.config.get("openai", {}).get("api_key")
        self.anthropic_key = anthropic_key or self.config.get("anthropic", {}).get("api_key")

        if self.openai_key:
            openai.api_key = self.openai_key

        self.anthropic_client = Anthropic(api_key=self.anthropic_key) if self.anthropic_key else None

    def complete(
        self,
        prompt: str,
        model: Optional[str] = None,
        provider: str = "auto",
        max_tokens: int = 500,
        temperature: float = 0.7,
        **kwargs,
    ) -> str:
        """Generate completion. provider: 'openai', 'anthropic', or 'auto'."""
        if provider == "auto":
            if self.openai_key:
                provider = "openai"
            elif self.anthropic_key:
                provider = "anthropic"
            else:
                raise RuntimeError("No LLM provider configured")

        if provider == "openai":
            return self._complete_openai(prompt, model, max_tokens, temperature, **kwargs)
        elif provider == "anthropic":
            return self._complete_anthropic(prompt, model, max_tokens, temperature, **kwargs)
        else:
            raise ValueError(f"Unknown provider: {provider}")

    def _complete_openai(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 500,
        temperature: float = 0.7,
        **kwargs,
    ) -> str:
        model = model or "gpt-3.5-turbo"
        try:
            resp = openai.ChatCompletion.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs,
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"OpenAI completion error: {e}")
            raise

    def _complete_anthropic(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 500,
        temperature: float = 0.7,
        **kwargs,
    ) -> str:
        model = model or "claude-3-opus-20240229"
        try:
            message = self.anthropic_client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}],
                **kwargs,
            )
            return message.content[0].text.strip()
        except Exception as e:
            logger.error(f"Anthropic completion error: {e}")
            raise

    def summarize(self, text: str, max_tokens: int = 300) -> str:
        """Summarize long text."""
        prompt = f"Summarize the following text in 3-4 concise sentences:\n\n{text}"
        return self.complete(prompt, max_tokens=max_tokens)

    def extract_entities(self, text: str, schema: Optional[Dict] = None) -> Dict[str, Any]:
        """Extract structured entities from text using guided prompting."""
        schema = schema or {"entities": ["product", "price", "brand"]}
        prompt = (
            "Extract the following information from the text. Respond in valid JSON.\n"
            f"Fields to extract: {schema}\n\n"
            f"Text:\n{text}"
        )
        try:
            import json
            result = self.complete(prompt, max_tokens=500)
            # Try to extract JSON block
            json_start = result.find("{")
            json_end = result.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                return json.loads(result[json_start:json_end])
            return {"raw": result}
        except Exception as e:
            logger.warning(f"Entity extraction failed: {e}")
            return {"error": str(e), "raw": result if 'result' in locals() else ""}
