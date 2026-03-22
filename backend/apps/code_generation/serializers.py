from rest_framework import serializers

from apps.code_generation.models import TestScript


class GenerateCodeRequestSerializer(serializers.Serializer):
    test_id = serializers.IntegerField(min_value=1)


class TestScriptSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestScript
        fields = ["id", "test_case", "language", "framework", "script_path", "created_at"]
