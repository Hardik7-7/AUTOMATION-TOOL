from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.code_generation.serializers import (
    GenerateCodeRequestSerializer,
    TestScriptSerializer,
)
from apps.code_generation.services import generate_script_for_test


class GenerateCodeAPIView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = GenerateCodeRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        test_id = serializer.validated_data["test_id"]
        try:
            script = generate_script_for_test(test_id)
        except Exception as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(TestScriptSerializer(script).data, status=status.HTTP_201_CREATED)
