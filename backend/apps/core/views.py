from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.models import LLMProvider
from apps.core.serializers import LLMProviderCreateSerializer


class LLMProviderCreateAPIView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = LLMProviderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if serializer.validated_data.get("is_active", True):
            LLMProvider.objects.update(is_active=False)

        provider = serializer.save()
        return Response(
            {"id": provider.id, "provider": provider.provider, "model_name": provider.model_name},
            status=status.HTTP_201_CREATED,
        )
