from rest_framework import serializers

from apps.core.models import LLMProvider


class LLMProviderCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = LLMProvider
        fields = ["provider", "api_key", "model_name", "is_active"]
