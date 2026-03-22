from rest_framework import serializers

from apps.test_generation.models import TestCase


class GenerateTestsRequestSerializer(serializers.Serializer):
    url = serializers.URLField(max_length=2048)


class TestCaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestCase
        fields = ["id", "source_url", "title", "description", "steps_json", "created_at"]
