from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.test_generation.serializers import (
    GenerateTestsRequestSerializer,
    TestCaseSerializer,
)
from apps.test_generation.services import generate_tests_from_url


class GenerateTestsAPIView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = GenerateTestsRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        url = serializer.validated_data["url"]
        try:
            test_cases = generate_tests_from_url(url)
        except Exception as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        output = TestCaseSerializer(test_cases, many=True).data
        return Response(output, status=status.HTTP_201_CREATED)
