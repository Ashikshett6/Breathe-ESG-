from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import SourceType
from core.permissions import IsOrgAnalyst
from core.serializers import IngestionBatchSerializer
from ingestion.parsers import run_ingestion


class UploadView(APIView):
    permission_classes = [IsAuthenticated, IsOrgAnalyst]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        source_type = request.data.get("source_type")
        file_obj = request.FILES.get("file")
        if not file_obj:
            return Response({"detail": "No file provided"}, status=status.HTTP_400_BAD_REQUEST)
        valid = {c[0] for c in SourceType.choices}
        if source_type not in valid:
            return Response(
                {"detail": f"source_type must be one of: {', '.join(valid)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        org = request.user.analystprofile.organization
        batch = run_ingestion(
            source_type, file_obj, file_obj.name, request.user, org
        )
        return Response(
            IngestionBatchSerializer(batch).data,
            status=status.HTTP_201_CREATED,
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsOrgAnalyst])
def source_types_view(request):
    return Response(
        [
            {
                "id": SourceType.SAP,
                "label": "SAP — fuel & procurement",
                "format": "CSV (semicolon or comma, English or German headers)",
                "scope": "1 / 3",
            },
            {
                "id": SourceType.UTILITY,
                "label": "Utility portal — electricity",
                "format": "CSV with billing period start/end and kWh",
                "scope": "2",
            },
            {
                "id": SourceType.TRAVEL,
                "label": "Corporate travel (Concur-style extract)",
                "format": "CSV expense extract",
                "scope": "3",
            },
        ]
    )
