from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from rest_framework.authtoken.models import Token

from pathlib import Path

from core.models import AnalystProfile, Organization, PlantLookup, SourceType
from ingestion.parsers import run_ingestion

REPO_ROOT = Path(__file__).resolve().parents[4]


class Command(BaseCommand):
    help = "Seed demo organization, analyst user, plant lookups, and sample ingests"

    def handle(self, *args, **options):
        org, _ = Organization.objects.get_or_create(
            slug="acme-corp",
            defaults={"name": "ACME Corporation (Demo)"},
        )
        plants = [
            ("1710", "Hamburg Manufacturing", "DE"),
            ("1720", "Munich Office", "DE"),
            ("US01", "Chicago Distribution", "US"),
        ]
        for code, name, country in plants:
            PlantLookup.objects.get_or_create(
                organization=org,
                code=code,
                defaults={"name": name, "country": country, "grid_region": "DE-LU" if country == "DE" else "US-MROW"},
            )

        user, created = User.objects.get_or_create(
            username="analyst",
            defaults={"email": "analyst@demo.breatheesg.local", "first_name": "Jordan", "last_name": "Lee"},
        )
        if created:
            user.set_password("demo1234")
            user.save()
        AnalystProfile.objects.get_or_create(
            user=user,
            defaults={"organization": org, "role": "analyst"},
        )
        token, _ = Token.objects.get_or_create(user=user)

        samples = REPO_ROOT / "samples"

        for st, fname in [
            (SourceType.SAP, "sap_procurement_q1.csv"),
            (SourceType.UTILITY, "utility_electricity_q1.csv"),
            (SourceType.TRAVEL, "concur_travel_q1.csv"),
        ]:
            path = samples / fname
            if path.exists():
                with open(path, "rb") as f:
                    run_ingestion(st, f, fname, user, org)

        self.stdout.write(self.style.SUCCESS("Demo seeded."))
        self.stdout.write(f"  Login: analyst / demo1234")
        self.stdout.write(f"  Token: {token.key}")
        self.stdout.write(f"  Org: {org.name}")
