from django.urls import path

from apps.code_generation.views import GenerateCodeAPIView


urlpatterns = [
    path("generate-code", GenerateCodeAPIView.as_view(), name="generate-code"),
]
