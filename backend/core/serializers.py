from django.contrib.auth.models import User
from rest_framework import serializers

from .models import (
    ActivityRecord,
    AnalystProfile,
    AuditEvent,
    IngestionBatch,
    Organization,
    PlantLookup,
)


class UserSerializer(serializers.ModelSerializer):
    organization = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name", "organization", "role"]

    def get_organization(self, obj):
        if hasattr(obj, "analystprofile"):
            return {
                "id": obj.analystprofile.organization_id,
                "name": obj.analystprofile.organization.name,
                "slug": obj.analystprofile.organization.slug,
            }
        return None

    def get_role(self, obj):
        if hasattr(obj, "analystprofile"):
            return obj.analystprofile.role
        return None


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ["id", "name", "slug"]


class PlantLookupSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlantLookup
        fields = ["id", "code", "name", "country", "grid_region"]


class IngestionBatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = IngestionBatch
        fields = [
            "id",
            "source_type",
            "filename",
            "uploaded_at",
            "status",
            "total_rows",
            "success_rows",
            "failed_rows",
            "flagged_rows",
            "error_summary",
        ]


class ActivityRecordSerializer(serializers.ModelSerializer):
    batch_filename = serializers.CharField(source="batch.filename", read_only=True)

    class Meta:
        model = ActivityRecord
        fields = [
            "id",
            "batch",
            "batch_filename",
            "source_type",
            "source_row_id",
            "scope",
            "category",
            "activity_date",
            "period_start",
            "period_end",
            "description",
            "site_code",
            "site_name",
            "vendor",
            "quantity",
            "unit",
            "normalized_quantity",
            "normalized_unit",
            "currency",
            "amount",
            "review_status",
            "flags",
            "validation_errors",
            "raw_payload",
            "ingested_at",
            "reviewed_at",
            "is_edited",
        ]
        read_only_fields = [
            "batch",
            "source_type",
            "source_row_id",
            "ingested_at",
            "raw_payload",
        ]


class ActivityRecordUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActivityRecord
        fields = [
            "quantity",
            "unit",
            "normalized_quantity",
            "normalized_unit",
            "description",
            "site_name",
            "activity_date",
        ]


class AuditEventSerializer(serializers.ModelSerializer):
    actor_name = serializers.CharField(source="actor.username", read_only=True)

    class Meta:
        model = AuditEvent
        fields = ["id", "action", "detail", "actor_name", "created_at", "activity", "batch"]


class DashboardStatsSerializer(serializers.Serializer):
    total_activities = serializers.IntegerField()
    pending = serializers.IntegerField()
    flagged = serializers.IntegerField()
    failed = serializers.IntegerField()
    approved = serializers.IntegerField()
    locked = serializers.IntegerField()
    by_scope = serializers.DictField()
    by_source = serializers.DictField()
    recent_batches = IngestionBatchSerializer(many=True)
