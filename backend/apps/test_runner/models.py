from django.db import models

from apps.test_generation.models import TestCase


class TestRun(models.Model):
    STATUS_RUNNING = "running"
    STATUS_PASSED = "passed"
    STATUS_FAILED = "failed"

    STATUS_CHOICES = [
        (STATUS_RUNNING, "Running"),
        (STATUS_PASSED, "Passed"),
        (STATUS_FAILED, "Failed"),
    ]

    test_case = models.ForeignKey(TestCase, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_RUNNING)
    logs = models.TextField(blank=True)
    failure_type = models.CharField(max_length=50, blank=True)
    failure_summary = models.TextField(blank=True)
    retry_count = models.IntegerField(default=0)
    started_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.id} - {self.test_case_id} - {self.status}"
