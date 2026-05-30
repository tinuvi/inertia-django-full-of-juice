from django.test import override_settings

from inertia.settings import settings as inertia_settings
from inertia.test import InertiaTestCase


class SettingsTestCase(InertiaTestCase):
    def test_ssr_exclude_defaults_to_empty(self):
        self.assertEqual(inertia_settings.INERTIA_SSR_EXCLUDE, [])

    @override_settings(INERTIA_SSR_EXCLUDE=[r"^/admin/"])
    def test_ssr_exclude_reads_from_django_settings(self):
        self.assertEqual(inertia_settings.INERTIA_SSR_EXCLUDE, [r"^/admin/"])

    @override_settings(INERTIA_VERSION="2.0")
    def test_version_works(self):
        response = self.inertia.get("/empty/", HTTP_X_INERTIA_VERSION="2.0")

        self.assertEqual(response.status_code, 200)

    def test_version_fallsback(self):
        response = self.inertia.get("/empty/", HTTP_X_INERTIA_VERSION="1.0")

        self.assertEqual(response.status_code, 200)

    def test_layout(self):
        response = self.client.get("/empty/")
        self.assertTemplateUsed(response, "layout.html")
