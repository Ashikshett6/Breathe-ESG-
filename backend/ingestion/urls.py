from django.urls import path

from . import views

urlpatterns = [
    path("ingest/upload/", views.UploadView.as_view()),
    path("ingest/sources/", views.source_types_view),
]
