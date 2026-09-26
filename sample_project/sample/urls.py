from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import include, path

urlpatterns = [
    path("", include("sample.apps.core.urls")),
]

# runserver serves static files on its own; gunicorn (the gevent E2E target)
# does not. No-op unless DEBUG=True.
urlpatterns += staticfiles_urlpatterns()
