from django.test import override_settings

from inertia.apps import check_ssr_exclude_patterns
from inertia.settings import resolve_inertia_version
from inertia.settings import settings as inertia_settings
from inertia.test import InertiaTestCase


class SettingsTestCase(InertiaTestCase):
    def test_ssr_exclude_defaults_to_empty(self):
        self.assertEqual(inertia_settings.INERTIA_SSR_EXCLUDE, [])

    @override_settings(INERTIA_SSR_EXCLUDE=[r"^/admin/"])
    def test_ssr_exclude_reads_from_django_settings(self):
        self.assertEqual(inertia_settings.INERTIA_SSR_EXCLUDE, [r"^/admin/"])


class SSRExcludeCheckTestCase(InertiaTestCase):
    def test_empty_default_produces_no_errors(self):
        self.assertEqual(check_ssr_exclude_patterns(None), [])

    @override_settings(INERTIA_SSR_EXCLUDE=[r"^/admin/", r"^/dashboard/"])
    def test_valid_patterns_produce_no_errors(self):
        self.assertEqual(check_ssr_exclude_patterns(None), [])

    @override_settings(INERTIA_SSR_EXCLUDE=[r"^/admin/", r"(unbalanced"])
    def test_invalid_pattern_reports_error(self):
        errors = check_ssr_exclude_patterns(None)

        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].id, "inertia.E001")
        self.assertIn("(unbalanced", errors[0].msg)

    @override_settings(INERTIA_SSR_EXCLUDE=[r"(", r"["])
    def test_each_invalid_pattern_reports_its_own_error(self):
        errors = check_ssr_exclude_patterns(None)

        self.assertEqual(len(errors), 2)
        self.assertTrue(all(e.id == "inertia.E001" for e in errors))

    @override_settings(INERTIA_VERSION="2.0")
    def test_version_works(self):
        response = self.inertia.get("/empty/", HTTP_X_INERTIA_VERSION="2.0")

        self.assertEqual(response.status_code, 200)

    def test_version_fallsback(self):
        response = self.inertia.get("/empty/", HTTP_X_INERTIA_VERSION="1.0")

        self.assertEqual(response.status_code, 200)


class ResolveInertiaVersionTestCase(InertiaTestCase):
    def test_default_is_the_string_one_dot_zero(self):
        self.assertEqual(resolve_inertia_version(), "1.0")

    @override_settings(INERTIA_VERSION="abc123")
    def test_plain_string_is_returned_as_is(self):
        self.assertEqual(resolve_inertia_version(), "abc123")

    @override_settings(INERTIA_VERSION=42)
    def test_non_string_value_is_cast_to_string(self):
        # Mirrors Laravel's `getVersion(): string` `(string) $version` cast.
        # Without it a non-string setting both leaks a non-string into the page
        # JSON and makes every GET stale (str header != int setting) → 409 loop.
        self.assertEqual(resolve_inertia_version(), "42")

    @override_settings(INERTIA_VERSION=lambda: "from-callable")
    def test_callable_is_invoked(self):
        self.assertEqual(resolve_inertia_version(), "from-callable")

    @override_settings(INERTIA_VERSION=lambda: 7)
    def test_callable_result_is_cast_to_string(self):
        self.assertEqual(resolve_inertia_version(), "7")

    @override_settings(INERTIA_VERSION=None)
    def test_none_resolves_to_empty_string(self):
        # Like Laravel's `(string) null === ''`: an unset version disables asset
        # versioning. The v3 client omits X-Inertia-Version when page.version is
        # falsy, so the empty string round-trips as "not stale".
        self.assertEqual(resolve_inertia_version(), "")

    @override_settings(INERTIA_VERSION=lambda: None)
    def test_callable_returning_none_resolves_to_empty_string(self):
        self.assertEqual(resolve_inertia_version(), "")

    def test_layout(self):
        response = self.client.get("/empty/")
        self.assertTemplateUsed(response, "layout.html")
