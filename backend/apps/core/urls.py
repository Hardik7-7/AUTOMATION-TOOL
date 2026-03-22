from django.urls import path

from apps.core.views import LLMProviderCreateAPIView


urlpatterns = [
    path("llm-config", LLMProviderCreateAPIView.as_view(), name="llm-config"),
]
