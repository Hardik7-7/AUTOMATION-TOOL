from django.urls import path

from apps.test_generation.views import GenerateTestsAPIView, TestCaseStatusAPIView


urlpatterns = [
    path("generate-tests", GenerateTestsAPIView.as_view(), name="generate-tests"),
    path("test-cases/<int:test_id>", TestCaseStatusAPIView.as_view(), name="test-case-status"),
]
