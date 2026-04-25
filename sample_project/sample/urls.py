from django.urls import include, path

urlpatterns = [
    path("", include("sample.apps.core.urls")),
]
