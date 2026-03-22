from django.db import models


class TestCase(models.Model):
    source_url = models.URLField(max_length=2048)
    title = models.CharField(max_length=255)
    description = models.TextField()
    steps_json = models.JSONField()
    steps_text = models.TextField(null=True, blank=True)
    raw_llm_output = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.id} - {self.title}"
