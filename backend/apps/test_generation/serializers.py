from rest_framework import serializers

from apps.test_generation.models import TestCase


class GenerateTestsRequestSerializer(serializers.Serializer):
    url = serializers.URLField(max_length=2048)
    product_description = serializers.CharField(required=False, allow_blank=True, max_length=5000)
    key_workflows = serializers.ListField(
        child=serializers.CharField(max_length=200),
        required=False,
        allow_empty=True,
    )


class TestCaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestCase
        fields = [
            "id",
            "source_url",
            "title",
            "description",
            "steps_json",
            "steps_text",
            "screenshots_json",
            "status",
            "created_at",
        ]


class TestCaseStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestCase
        fields = ["status"]
