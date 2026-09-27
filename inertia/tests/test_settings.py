import math

from django.core.management import call_command
from django.core.management.base import SystemCheckError
from django.test import override_settings
from urllib3.util import Timeout as Urllib3Timeout

from inertia.apps import check_ssr_exclude_patterns, check_ssr_timeout
from inertia.settings import resolve_inertia_version
from inertia.settings import settings as inertia_settings
from inertia.test import InertiaTestCase


class SettingsTestCase(InertiaTestCase):
    def test_ssr_exclude_defaults_to_empty(self):
        self.assertEqual(inertia_settings.INERTIA_SSR_EXCLUDE, [])

    @override_settings(INERTIA_SSR_EXCLUDE=[r"^/admin/"])
    def test_ssr_exclude_reads_from_django_settings(self):
        self.assertEqual(inertia_settings.INERTIA_SSR_EXCLUDE, [r"^/admin/"])

    def test_ssr_timeout_defaults_to_five_seconds(self):
        self.assertEqual(inertia_settings.INERTIA_SSR_TIMEOUT, 5.0)

    @override_settings(INERTIA_SSR_TIMEOUT=2)
    def test_ssr_timeout_reads_from_django_settings(self):
        self.assertEqual(inertia_settings.INERTIA_SSR_TIMEOUT, 2)


class SSRTimeoutCheckTestCase(InertiaTestCase):
    def test_default_produces_no_errors(self):
        self.assertEqual(check_ssr_timeout(None), [])

    def test_valid_values_produce_no_errors(self):
        for value in (
            1,
            2.5,
            0.01,
            1e9,
            None,
            (1, 5),
            (0.5, 2.5),
            (None, 5),
            (5, None),
            (None, None),
        ):
            with (
                self.subTest(value=value),
                override_settings(INERTIA_SSR_TIMEOUT=value),
            ):
                self.assertEqual(check_ssr_timeout(None), [])

    def test_invalid_values_report_an_error(self):
        for value in (
            "4",
            0,
            -1,
            0.0,
            True,
            False,
            (1,),
            (1, 2, 3),
            [1, 2],
            (1, "5"),
            (0, 5),
            (5, -1),
            (True, 5),
            math.inf,
            -math.inf,
            math.nan,
            (5, math.inf),
            # requests accepts a urllib3 ``Timeout`` too, but it is not part of
            # the setting's contract: its ``total`` is no wall-clock cap either.
            Urllib3Timeout(total=2),
        ):
            with (
                self.subTest(value=value),
                override_settings(INERTIA_SSR_TIMEOUT=value),
            ):
                errors = check_ssr_timeout(None)

                self.assertEqual(len(errors), 1)
                self.assertEqual(errors[0].id, "inertia.E002")
                self.assertIn(repr(value), errors[0].msg)
                self.assertIn("float()", errors[0].hint)

    @override_settings(INERTIA_SSR_TIMEOUT="4")
    def test_the_check_is_registered_and_fails_manage_py_check(self):
        with self.assertRaisesMessage(SystemCheckError, "inertia.E002"):
            call_command("check")


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
