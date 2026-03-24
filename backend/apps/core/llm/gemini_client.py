from dataclasses import dataclass

import google.generativeai as genai

from apps.core.models import LLMProvider
import base64

@dataclass
class GeminiResponse:
    text: str
    raw: object


class GeminiClient:
    def __init__(self) -> None:
        provider = LLMProvider.objects.filter(is_active=True).order_by("-created_at").first()
        if not provider:
            raise ValueError("No active LLM provider configured")
        if provider.provider != LLMProvider.PROVIDER_GEMINI:
            raise ValueError(f"Unsupported provider: {provider.provider}")

        genai.configure(api_key=provider.api_key)
        self.model_name = provider.model_name or "gemini-1.5-flash"
        self.model = genai.GenerativeModel(self.model_name)

    def generate_text(self, prompt: str, image_parts: list[dict] | None = None) -> GeminiResponse:
        if image_parts:
            # Gemini multimodal: text first, then images
            contents = [prompt] + [
                {"mime_type": part["inline_data"]["mime_type"],
                "data": base64.b64decode(part["inline_data"]["data"])}
                for part in image_parts
            ]
            response = self.model.generate_content(contents)
        else:
            response = self.model.generate_content(prompt)

        text = getattr(response, "text", None) or str(response)
        return GeminiResponse(text=text, raw=response)
