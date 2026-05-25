from django.conf import settings
from django.db import models


class Organization(models.Model):
    """Tenant boundary — all emissions data is scoped to one organization."""

    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class AnalystProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    role = models.CharField(
        max_length=32,
        choices=[("analyst", "Analyst"), ("admin", "Admin")],
        default="analyst",
    )

    def __str__(self):
        return f"{self.user.username} @ {self.organization.slug}"


class PlantLookup(models.Model):
    """Maps opaque SAP plant codes to human-readable sites."""

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="plants"
    )
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=200)
    country = models.CharField(max_length=2, blank=True)
    grid_region = models.CharField(max_length=64, blank=True)

    class Meta:
        unique_together = [("organization", "code")]
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} — {self.name}"


class Scope(models.TextChoices):
    SCOPE_1 = "1", "Scope 1"
    SCOPE_2 = "2", "Scope 2"
    SCOPE_3 = "3", "Scope 3"


class SourceType(models.TextChoices):
    SAP = "sap", "SAP (fuel & procurement)"
    UTILITY = "utility", "Utility portal"
    TRAVEL = "travel", "Corporate travel"


class ActivityCategory(models.TextChoices):
    FUEL = "fuel", "Fuel combustion"
    PROCUREMENT = "procurement", "Purchased goods"
    ELECTRICITY = "electricity", "Purchased electricity"
    FLIGHT = "flight", "Air travel"
    HOTEL = "hotel", "Hotel stay"
    GROUND = "ground", "Ground transport"


class ReviewStatus(models.TextChoices):
    PENDING = "pending", "Pending review"
    FLAGGED = "flagged", "Flagged — needs attention"
    FAILED = "failed", "Failed validation"
    APPROVED = "approved", "Approved"
    LOCKED = "locked", "Locked for audit"


class IngestionBatch(models.Model):
    """One upload or extract pull from a single source."""

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="batches"
    )
    source_type = models.CharField(max_length=16, choices=SourceType.choices)
    filename = models.CharField(max_length=255)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=16,
        choices=[
            ("processing", "Processing"),
            ("completed", "Completed"),
            ("partial", "Partial — some rows failed"),
            ("failed", "Failed"),
        ],
        default="processing",
    )
    total_rows = models.PositiveIntegerField(default=0)
    success_rows = models.PositiveIntegerField(default=0)
    failed_rows = models.PositiveIntegerField(default=0)
    flagged_rows = models.PositiveIntegerField(default=0)
    error_summary = models.TextField(blank=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"{self.source_type} — {self.filename} ({self.uploaded_at:%Y-%m-%d})"


class ActivityRecord(models.Model):
    """
    Normalized activity row — the unit analysts review before audit lock.
    Source-of-truth: which batch/file produced this row; edits tracked in AuditEvent.
    """

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="activities"
    )
    batch = models.ForeignKey(
        IngestionBatch, on_delete=models.CASCADE, related_name="activities"
    )
    source_type = models.CharField(max_length=16, choices=SourceType.choices)
    source_row_id = models.CharField(max_length=128, help_text="Stable ID from source file")
    source_row_hash = models.CharField(max_length=64)

    scope = models.CharField(max_length=1, choices=Scope.choices)
    category = models.CharField(max_length=32, choices=ActivityCategory.choices)

    activity_date = models.DateField(null=True, blank=True)
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)

    description = models.CharField(max_length=500, blank=True)
    site_code = models.CharField(max_length=64, blank=True)
    site_name = models.CharField(max_length=200, blank=True)
    vendor = models.CharField(max_length=200, blank=True)

    quantity = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True)
    unit = models.CharField(max_length=32, blank=True)
    normalized_quantity = models.DecimalField(
        max_digits=18, decimal_places=6, null=True, blank=True
    )
    normalized_unit = models.CharField(max_length=32, blank=True)

    currency = models.CharField(max_length=3, blank=True)
    amount = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)

    review_status = models.CharField(
        max_length=16, choices=ReviewStatus.choices, default=ReviewStatus.PENDING
    )
    flags = models.JSONField(default=list, blank=True)
    validation_errors = models.JSONField(default=list, blank=True)

    raw_payload = models.JSONField(default=dict, blank=True)

    ingested_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_activities",
    )
    is_edited = models.BooleanField(default=False)

    class Meta:
        ordering = ["-activity_date", "-ingested_at"]
        indexes = [
            models.Index(fields=["organization", "review_status"]),
            models.Index(fields=["organization", "scope", "category"]),
            models.Index(fields=["batch"]),
        ]
        unique_together = [("organization", "source_type", "source_row_hash")]

    def __str__(self):
        return f"{self.category} {self.quantity} {self.unit} ({self.review_status})"


class AuditEvent(models.Model):
    """Immutable audit trail for analyst actions and field edits."""

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    activity = models.ForeignKey(
        ActivityRecord,
        on_delete=models.CASCADE,
        related_name="audit_events",
        null=True,
        blank=True,
    )
    batch = models.ForeignKey(
        IngestionBatch,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="audit_events",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    action = models.CharField(max_length=64)
    detail = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
