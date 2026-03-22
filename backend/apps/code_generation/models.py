from django.db import models

from apps.test_generation.models import TestCase


class TestScript(models.Model):
    test_case = models.ForeignKey(TestCase, on_delete=models.CASCADE)
    language = models.CharField(max_length=50, default="python")
    framework = models.CharField(max_length=50, default="playwright_sync")
    script_path = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.id} - {self.test_case_id}"
