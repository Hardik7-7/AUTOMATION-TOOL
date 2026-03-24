from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.test_runner.services import run_test_by_case_id


class RunTestAPIView(APIView):
    def post(self, request, test_id: int, *args, **kwargs):
        try:
            test_run, snippet = run_test_by_case_id(test_id)
        except FileNotFoundError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_404_NOT_FOUND)
        except Exception as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                "test_run_id": test_run.id,
                "status": test_run.status,
                "log_snippet": snippet,
            },
            status=status.HTTP_200_OK,
        )
