from django.contrib import admin
from django.urls import include, path, re_path
from django.views.generic import TemplateView
from django.views.static import serve
from django.conf import settings

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("core.urls")),
    path("api/", include("ingestion.urls")),
]

_dist = settings.REPO_ROOT / "frontend" / "dist"
if (_dist / "index.html").exists():
    urlpatterns += [
        path(
            "assets/<path:path>",
            serve,
            {"document_root": _dist / "assets"},
        ),
        re_path(
            r"^(?!api/|admin/|static/|assets/).*$",
            TemplateView.as_view(template_name="index.html"),
            name="spa",
        ),
    ]
