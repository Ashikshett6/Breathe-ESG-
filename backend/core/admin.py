from django.contrib import admin

from .models import (
    ActivityRecord,
    AnalystProfile,
    AuditEvent,
    IngestionBatch,
    Organization,
    PlantLookup,
)


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "created_at"]


@admin.register(AnalystProfile)
class AnalystProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "organization", "role"]


@admin.register(PlantLookup)
class PlantLookupAdmin(admin.ModelAdmin):
    list_display = ["organization", "code", "name", "country"]


@admin.register(IngestionBatch)
class IngestionBatchAdmin(admin.ModelAdmin):
    list_display = [
        "filename",
        "source_type",
        "organization",
        "status",
        "success_rows",
        "failed_rows",
        "uploaded_at",
    ]


@admin.register(ActivityRecord)
class ActivityRecordAdmin(admin.ModelAdmin):
    list_display = [
        "category",
        "scope",
        "quantity",
        "unit",
        "review_status",
        "activity_date",
        "organization",
    ]
    list_filter = ["review_status", "scope", "source_type", "category"]


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ["action", "actor", "organization", "created_at"]
