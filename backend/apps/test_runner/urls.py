from django.urls import path

from apps.test_runner.views import RunTestAPIView


urlpatterns = [
    path("run-test/<int:test_id>", RunTestAPIView.as_view(), name="run-test"),
]
