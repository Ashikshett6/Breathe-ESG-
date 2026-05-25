from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.db.models import Count
from rest_framework import status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import (
    ActivityRecord,
    AuditEvent,
    IngestionBatch,
    PlantLookup,
    ReviewStatus,
)
from .permissions import IsOrgAnalyst
from .serializers import (
    ActivityRecordSerializer,
    ActivityRecordUpdateSerializer,
    AuditEventSerializer,
    DashboardStatsSerializer,
    IngestionBatchSerializer,
    PlantLookupSerializer,
    UserSerializer,
)


def _org(request):
    return request.user.analystprofile.organization


def _log_audit(org, actor, action, detail=None, activity=None, batch=None):
    AuditEvent.objects.create(
        organization=org,
        actor=actor,
        action=action,
        detail=detail or {},
        activity=activity,
        batch=batch,
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def login_view(request):
    username = request.data.get("username")
    password = request.data.get("password")
    user = authenticate(username=username, password=password)
    if not user:
        return Response({"detail": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)
    if not hasattr(user, "analystprofile"):
        return Response({"detail": "User is not an analyst"}, status=status.HTTP_403_FORBIDDEN)
    token, _ = Token.objects.get_or_create(user=user)
    return Response({"token": token.key, "user": UserSerializer(user).data})


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsOrgAnalyst])
def me_view(request):
    return Response(UserSerializer(request.user).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsOrgAnalyst])
def dashboard_view(request):
    org = _org(request)
    qs = ActivityRecord.objects.filter(organization=org)
    status_counts = {s: 0 for s in ReviewStatus.values}
    for row in qs.values("review_status").annotate(c=Count("id")):
        status_counts[row["review_status"]] = row["c"]

    by_scope = {
        str(r["scope"]): r["c"]
        for r in qs.values("scope").annotate(c=Count("id"))
    }
    by_source = {
        r["source_type"]: r["c"]
        for r in qs.values("source_type").annotate(c=Count("id"))
    }
    recent = IngestionBatch.objects.filter(organization=org)[:5]
    data = {
        "total_activities": qs.count(),
        "pending": status_counts.get("pending", 0),
        "flagged": status_counts.get("flagged", 0),
        "failed": status_counts.get("failed", 0),
        "approved": status_counts.get("approved", 0),
        "locked": status_counts.get("locked", 0),
        "by_scope": by_scope,
        "by_source": by_source,
        "recent_batches": IngestionBatchSerializer(recent, many=True).data,
    }
    return Response(DashboardStatsSerializer(data).data)


class ActivityViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ActivityRecordSerializer
    permission_classes = [IsAuthenticated, IsOrgAnalyst]
    filterset_fields = ["review_status", "scope", "source_type", "category", "batch"]
    search_fields = ["description", "site_name", "vendor", "source_row_id"]
    ordering_fields = ["activity_date", "ingested_at", "quantity"]

    def get_queryset(self):
        return ActivityRecord.objects.filter(organization=_org(self.request))

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        activity = self.get_object()
        if activity.review_status == ReviewStatus.LOCKED:
            return Response(
                {"detail": "Row is locked for audit"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        old = activity.review_status
        activity.review_status = ReviewStatus.APPROVED
        activity.reviewed_by = request.user
        from django.utils import timezone

        activity.reviewed_at = timezone.now()
        activity.save()
        _log_audit(
            activity.organization,
            request.user,
            "approve",
            {"from": old, "to": "approved"},
            activity=activity,
        )
        return Response(ActivityRecordSerializer(activity).data)

    @action(detail=True, methods=["post"])
    def flag(self, request, pk=None):
        activity = self.get_object()
        if activity.review_status == ReviewStatus.LOCKED:
            return Response(
                {"detail": "Row is locked for audit"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        reason = request.data.get("reason", "Manual flag by analyst")
        flags = list(activity.flags or [])
        if reason not in flags:
            flags.append(reason)
        activity.flags = flags
        activity.review_status = ReviewStatus.FLAGGED
        activity.save()
        _log_audit(
            activity.organization,
            request.user,
            "flag",
            {"reason": reason},
            activity=activity,
        )
        return Response(ActivityRecordSerializer(activity).data)

    @action(detail=True, methods=["patch"])
    def edit(self, request, pk=None):
        activity = self.get_object()
        if activity.review_status == ReviewStatus.LOCKED:
            return Response(
                {"detail": "Row is locked for audit"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        ser = ActivityRecordUpdateSerializer(activity, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        changes = {}
        for field, new_val in ser.validated_data.items():
            old_val = getattr(activity, field)
            if str(old_val) != str(new_val):
                changes[field] = {"from": str(old_val), "to": str(new_val)}
        ser.save()
        if changes:
            activity.is_edited = True
            activity.save(update_fields=["is_edited"])
            _log_audit(
                activity.organization,
                request.user,
                "edit",
                changes,
                activity=activity,
            )
        return Response(ActivityRecordSerializer(activity).data)

    @action(detail=False, methods=["post"])
    def bulk_approve(self, request):
        ids = request.data.get("ids", [])
        org = _org(request)
        updated = []
        for activity in ActivityRecord.objects.filter(
            organization=org, id__in=ids
        ).exclude(review_status=ReviewStatus.LOCKED):
            activity.review_status = ReviewStatus.APPROVED
            activity.reviewed_by = request.user
            from django.utils import timezone

            activity.reviewed_at = timezone.now()
            activity.save()
            updated.append(activity.id)
            _log_audit(org, request.user, "approve", {"bulk": True}, activity=activity)
        return Response({"approved": updated})

    @action(detail=False, methods=["post"])
    def lock_approved(self, request):
        """Lock all approved rows for external audit — irreversible in prototype."""
        org = _org(request)
        count = ActivityRecord.objects.filter(
            organization=org, review_status=ReviewStatus.APPROVED
        ).update(review_status=ReviewStatus.LOCKED)
        _log_audit(org, request.user, "lock_for_audit", {"count": count})
        return Response({"locked_count": count})


class BatchViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = IngestionBatchSerializer
    permission_classes = [IsAuthenticated, IsOrgAnalyst]

    def get_queryset(self):
        return IngestionBatch.objects.filter(organization=_org(self.request))


class PlantViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PlantLookupSerializer
    permission_classes = [IsAuthenticated, IsOrgAnalyst]

    def get_queryset(self):
        return PlantLookup.objects.filter(organization=_org(self.request))


class AuditViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AuditEventSerializer
    permission_classes = [IsAuthenticated, IsOrgAnalyst]

    def get_queryset(self):
        return AuditEvent.objects.filter(organization=_org(self.request))[:200]
