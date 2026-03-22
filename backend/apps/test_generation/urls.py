from django.urls import path

from apps.test_generation.views import GenerateTestsAPIView


urlpatterns = [
    path("generate-tests", GenerateTestsAPIView.as_view(), name="generate-tests"),
]
