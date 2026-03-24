from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.test_generation.serializers import (
    GenerateTestsRequestSerializer,
    TestCaseSerializer,
    TestCaseStatusUpdateSerializer,
)
from apps.test_generation.services import generate_tests_from_url
from apps.test_generation.models import TestCase


class GenerateTestsAPIView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = GenerateTestsRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        url = serializer.validated_data["url"]
        product_description = serializer.validated_data.get("product_description")
        key_workflows = serializer.validated_data.get("key_workflows")
        try:
            test_cases = generate_tests_from_url(
                url,
                product_description=product_description,
                key_workflows=key_workflows,
            )
        except Exception as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        output = TestCaseSerializer(test_cases, many=True).data
        return Response(output, status=status.HTTP_201_CREATED)


class TestCaseStatusAPIView(APIView):
    def patch(self, request, test_id: int, *args, **kwargs):
        test_case = TestCase.objects.get(id=test_id)
        serializer = TestCaseStatusUpdateSerializer(test_case, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(TestCaseSerializer(test_case).data, status=status.HTTP_200_OK)
