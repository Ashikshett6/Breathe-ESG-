from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("activities", views.ActivityViewSet, basename="activities")
router.register("batches", views.BatchViewSet, basename="batches")
router.register("plants", views.PlantViewSet, basename="plants")
router.register("audit", views.AuditViewSet, basename="audit")

urlpatterns = [
    path("auth/login/", views.login_view),
    path("auth/me/", views.me_view),
    path("dashboard/", views.dashboard_view),
    path("", include(router.urls)),
]
