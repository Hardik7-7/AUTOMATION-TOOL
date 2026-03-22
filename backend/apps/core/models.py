from django.db import models


class LLMProvider(models.Model):
    PROVIDER_GEMINI = "gemini"

    PROVIDER_CHOICES = [
        (PROVIDER_GEMINI, "Gemini"),
    ]

    provider = models.CharField(max_length=50, choices=PROVIDER_CHOICES)
    api_key = models.TextField()
    model_name = models.CharField(max_length=200, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.provider} ({self.model_name or 'default'})"
