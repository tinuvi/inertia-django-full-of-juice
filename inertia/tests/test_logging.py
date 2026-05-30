"""Tests for the library's DEBUG logging surface.

These verify that the protocol decision points emit deterministic log
records on the ``inertia_django_full_of_juice`` logger. The E2E
checklist in ``sample_project/E2E_TESTING.md`` correlates these log
lines with browser actions, so the assertions here pin the
human-readable phrasing as well as the conditions under which each
record fires.
"""

import logging

from django.test import override_settings

from inertia.http import (
    clear_history,
    encrypt_history,
    errors_response,
    inertia_redirect,
    location,
    preserve_fragment,
)
from inertia.test import InertiaTestCase

_LOGGER = "inertia_django_full_of_juice"


def _messages(records: list[logging.LogRecord]) -> list[str]:
    return [r.getMessage() for r in records]


class PageShellLoggingTestCase(InertiaTestCase):
    def test_first_load_logs_component_url_and_conditional_fields(self):
        with self.assertLogs(_LOGGER, level="DEBUG") as cm:
            self.client.get("/empty/")

        messages = _messages(cm.records)
        page_shell = [m for m in messages if m.startswith("page-shell: component=")]
        self.assertTrue(page_shell, msg=messages)
        self.assertIn("conditional_fields=[]", page_shell[-1])

    def test_partial_render_logs_partial_data_and_partial_except(self):
        with self.assertLogs(_LOGGER, level="DEBUG") as cm:
            self.inertia.get(
                "/props/",
                HTTP_X_INERTIA_PARTIAL_DATA="name",
                HTTP_X_INERTIA_PARTIAL_EXCEPT="sport",
                HTTP_X_INERTIA_PARTIAL_COMPONENT="TestComponent",
            )

        messages = _messages(cm.records)
        build_props = [m for m in messages if m.startswith("build_props: component=")]
        self.assertTrue(build_props, msg=messages)
        self.assertIn("is_partial=True", build_props[-1])
        self.assertIn("partial_data=['name']", build_props[-1])
        self.assertIn("partial_except=['sport']", build_props[-1])

    def test_encrypt_history_emit_logs(self):
        with self.assertLogs(_LOGGER, level="DEBUG") as cm:
            self.client.get("/encrypt-history/")

        self.assertIn(
            "page-shell: emitting encryptHistory=True for component='TestComponent'",
            _messages(cm.records),
        )

    def test_clear_history_consumed_logs(self):
        with self.assertLogs(_LOGGER, level="DEBUG") as cm:
            self.client.get("/clear-history-redirect/")
            self.client.get("/empty/")

        emit = [
            m
            for m in _messages(cm.records)
            if m.startswith("page-shell: emitting clearHistory=True")
        ]
        self.assertTrue(emit)

    def test_preserve_fragment_consumed_logs(self):
        with self.assertLogs(_LOGGER, level="DEBUG") as cm:
            self.client.get("/preserve-fragment/")

        emit = [
            m
            for m in _messages(cm.records)
            if m.startswith("page-shell: emitting preserveFragment=True")
        ]
        self.assertTrue(emit)


class BuildPropsLoggingTestCase(InertiaTestCase):
    def test_drop_partial_data_filtered_prop(self):
        with self.assertLogs(_LOGGER, level="DEBUG") as cm:
            self.inertia.get(
                "/props/",
                HTTP_X_INERTIA_PARTIAL_DATA="name",
                HTTP_X_INERTIA_PARTIAL_COMPONENT="TestComponent",
            )

        self.assertIn(
            "build_props: dropping prop 'sport' because it is not in X-Inertia-Partial-Data",
            _messages(cm.records),
        )

    def test_drop_partial_except_filtered_prop(self):
        with self.assertLogs(_LOGGER, level="DEBUG") as cm:
            self.inertia.get(
                "/partial-except/",
                HTTP_X_INERTIA_PARTIAL_EXCEPT="team",
                HTTP_X_INERTIA_PARTIAL_COMPONENT="TestComponent",
            )

        self.assertIn(
            "build_props: dropping prop 'team' because it is in X-Inertia-Partial-Except",
            _messages(cm.records),
        )

    def test_drop_ignore_on_first_load_logs_class_name(self):
        with self.assertLogs(_LOGGER, level="DEBUG") as cm:
            self.client.get("/optional/")

        msgs = _messages(cm.records)
        sport = [
            m
            for m in msgs
            if "build_props: dropping prop 'sport' on first load" in m
            and "OptionalProp" in m
        ]
        self.assertTrue(sport, msg=msgs)

    def test_drop_always_included_on_partial_except(self):
        with self.assertLogs(_LOGGER, level="DEBUG") as cm:
            self.inertia.get(
                "/empty/",
                HTTP_X_INERTIA_PARTIAL_EXCEPT="errors",
                HTTP_X_INERTIA_PARTIAL_COMPONENT="TestComponent",
            )

        self.assertIn(
            "build_props: dropping always-included prop 'errors' because it is in X-Inertia-Partial-Except",
            _messages(cm.records),
        )


class OnceLoggingTestCase(InertiaTestCase):
    def test_skip_once_due_to_except_once(self):
        with self.assertLogs(_LOGGER, level="DEBUG") as cm:
            self.inertia.get("/once/", HTTP_X_INERTIA_EXCEPT_ONCE_PROPS="plans")

        self.assertIn(
            "build_props: skipping once prop 'plans' (registry key='plans') because it is in X-Inertia-Except-Once-Props",
            _messages(cm.records),
        )

    def test_fresh_overrides_except_once_logs_survival(self):
        with self.assertLogs(_LOGGER, level="DEBUG") as cm:
            self.inertia.get("/once-fresh/", HTTP_X_INERTIA_EXCEPT_ONCE_PROPS="plans")

        self.assertIn(
            "build_props: once prop 'plans' (registry key='plans') survives X-Inertia-Except-Once-Props because fresh=True",
            _messages(cm.records),
        )

    def test_partial_data_overrides_except_once_logs_survival(self):
        with self.assertLogs(_LOGGER, level="DEBUG") as cm:
            self.inertia.get(
                "/once/",
                HTTP_X_INERTIA_EXCEPT_ONCE_PROPS="plans",
                HTTP_X_INERTIA_PARTIAL_DATA="plans",
                HTTP_X_INERTIA_PARTIAL_COMPONENT="TestComponent",
            )

        self.assertIn(
            "build_props: once prop 'plans' (registry key='plans') survives X-Inertia-Except-Once-Props because it is in X-Inertia-Partial-Data",
            _messages(cm.records),
        )

    def test_emit_once_registry(self):
        with self.assertLogs(_LOGGER, level="DEBUG") as cm:
            self.client.get("/once/")

        emit = [
            m
            for m in _messages(cm.records)
            if m.startswith("build_once_props: emitting onceProps=")
        ]
        self.assertTrue(emit)
        self.assertIn("'plans'", emit[-1])


class DeferredLoggingTestCase(InertiaTestCase):
    def test_emit_deferred_groups_on_first_load(self):
        with self.assertLogs(_LOGGER, level="DEBUG") as cm:
            self.client.get("/defer-group/")

        emit = [
            m
            for m in _messages(cm.records)
            if m.startswith("build_deferred_props: emitting deferredProps=")
        ]
        self.assertTrue(emit)
        self.assertIn("'group'", emit[-1])

    def test_suppress_deferred_on_partial_render(self):
        with self.assertLogs(_LOGGER, level="DEBUG") as cm:
            self.inertia.get(
                "/defer/",
                HTTP_X_INERTIA_PARTIAL_DATA="sport",
                HTTP_X_INERTIA_PARTIAL_COMPONENT="TestComponent",
            )

        self.assertIn(
            "build_deferred_props: suppressing deferredProps on partial render of component='TestComponent'",
            _messages(cm.records),
        )


class MergeLoggingTestCase(InertiaTestCase):
    def test_emit_merge_metadata(self):
        with self.assertLogs(_LOGGER, level="DEBUG") as cm:
            self.client.get("/merge-match-on/")

        emit = [
            m
            for m in _messages(cm.records)
            if m.startswith("build_merge_kinds: mergeProps=")
        ]
        self.assertTrue(emit)
        self.assertIn("['users']", emit[-1])
        self.assertIn("['users.id']", emit[-1])

    def test_drop_merge_metadata_on_reset(self):
        with self.assertLogs(_LOGGER, level="DEBUG") as cm:
            self.inertia.get(
                "/merge-match-on/",
                HTTP_X_INERTIA_RESET="users",
                HTTP_X_INERTIA_PARTIAL_COMPONENT="TestComponent",
            )

        self.assertIn(
            "build_merge_kinds: dropping merge metadata for 'users' because it is in X-Inertia-Reset",
            _messages(cm.records),
        )

    def test_drop_once_registry_on_reset(self):
        with self.assertLogs(_LOGGER, level="DEBUG") as cm:
            self.inertia.get(
                "/once/",
                HTTP_X_INERTIA_RESET="plans",
                HTTP_X_INERTIA_PARTIAL_COMPONENT="TestComponent",
            )

        self.assertIn(
            "build_once_props: dropping once registry entry for 'plans' because it is in X-Inertia-Reset",
            _messages(cm.records),
        )


class ScrollLoggingTestCase(InertiaTestCase):
    def test_emit_scroll_props(self):
        with self.assertLogs(_LOGGER, level="DEBUG") as cm:
            self.client.get("/infinite-scroll-pagination/")

        emit = [
            m
            for m in _messages(cm.records)
            if m.startswith("build_scroll_props: emitting scrollProps=")
        ]
        self.assertTrue(emit)
        self.assertIn("'items'", emit[-1])
        self.assertIn("'pageName': 'cursor'", emit[-1])

    def test_infinite_scroll_merge_strategy_logs_intent_and_choice(self):
        with self.assertLogs(_LOGGER, level="DEBUG") as cm:
            self.inertia.get(
                "/infinite-scroll/",
                HTTP_X_INERTIA_INFINITE_SCROLL_MERGE_INTENT="prepend",
            )

        self.assertIn(
            "InfiniteScrollProp: X-Inertia-Infinite-Scroll-Merge-Intent='prepend' → strategy=prepend",
            _messages(cm.records),
        )

    def test_infinite_scroll_merge_strategy_defaults_to_append(self):
        with self.assertLogs(_LOGGER, level="DEBUG") as cm:
            self.inertia.get("/infinite-scroll/")

        self.assertIn(
            "InfiniteScrollProp: X-Inertia-Infinite-Scroll-Merge-Intent='' → strategy=append",
            _messages(cm.records),
        )


class FirstLoadShellLoggingTestCase(InertiaTestCase):
    def test_first_load_inline_json_log(self):
        with self.assertLogs(_LOGGER, level="DEBUG") as cm:
            self.client.get("/props/")

        emit = [
            m
            for m in _messages(cm.records)
            if m.startswith("first-load shell: rendering inline JSON")
        ]
        self.assertTrue(emit)
        self.assertIn("escaped_chars_added=", emit[-1])


class HelperLoggingTestCase(InertiaTestCase):
    def test_location_helper_logs(self):
        with self.assertLogs(_LOGGER, level="DEBUG") as cm:
            location("https://example.com/")

        self.assertIn(
            "location(): emitting 409 with X-Inertia-Location='https://example.com/'",
            _messages(cm.records),
        )

    def test_inertia_redirect_helper_logs(self):
        with self.assertLogs(_LOGGER, level="DEBUG") as cm:
            inertia_redirect("/lists/")

        self.assertIn(
            "inertia_redirect(): emitting 409 with X-Inertia-Redirect='/lists/'",
            _messages(cm.records),
        )

    def test_errors_response_logs(self):
        with self.assertLogs(_LOGGER, level="DEBUG") as cm:
            errors_response({"name": "Required", "email": "Invalid"})

        emit = [
            m
            for m in _messages(cm.records)
            if m.startswith("errors_response(): status=422")
        ]
        self.assertTrue(emit)
        self.assertIn("['email', 'name']", emit[-1])

    def test_encrypt_history_logs(self):
        from django.test import RequestFactory

        request = RequestFactory().get("/")
        with self.assertLogs(_LOGGER, level="DEBUG") as cm:
            encrypt_history(request)

        self.assertIn(
            "encrypt_history(): set request flag to True", _messages(cm.records)
        )

    def test_clear_history_logs(self):
        request = self.client.get("/empty/").wsgi_request
        with self.assertLogs(_LOGGER, level="DEBUG") as cm:
            clear_history(request)

        self.assertIn(
            "clear_history(): set session flash flag (one-shot)",
            _messages(cm.records),
        )

    def test_preserve_fragment_logs(self):
        request = self.client.get("/empty/").wsgi_request
        with self.assertLogs(_LOGGER, level="DEBUG") as cm:
            preserve_fragment(request)

        self.assertIn(
            "preserve_fragment(): set session flash flag (one-shot)",
            _messages(cm.records),
        )


class MiddlewareLoggingTestCase(InertiaTestCase):
    def test_middleware_summary_logs_method_path_inertia_status(self):
        with self.assertLogs(_LOGGER, level="DEBUG") as cm:
            self.inertia.get("/empty/")

        emit = [m for m in _messages(cm.records) if m.startswith("middleware: method=")]
        self.assertTrue(emit)
        self.assertIn("is_inertia=True", emit[-1])
        self.assertIn("downstream_status=200", emit[-1])

    def test_middleware_logs_fragment_redirect_rewrite(self):
        with self.assertLogs(_LOGGER, level="DEBUG") as cm:
            self.inertia.get("/fragment-redirect/")

        emit = [
            m
            for m in _messages(cm.records)
            if m.startswith("middleware: fragment redirect detected")
        ]
        self.assertTrue(emit)
        self.assertIn("/empty/#section", emit[-1])

    def test_middleware_logs_method_conversion_to_303(self):
        with self.assertLogs(_LOGGER, level="DEBUG") as cm:
            self.inertia.put("/redirect/")

        self.assertIn(
            "middleware: converting PUT redirect from 302 to 303 (per v3 method-conversion contract)",
            _messages(cm.records),
        )

    def test_middleware_logs_stale_version(self):
        with self.assertLogs(_LOGGER, level="DEBUG") as cm:
            self.inertia.get(
                "/empty/",
                HTTP_X_INERTIA_VERSION="some-nonsense",
            )

        emit = [
            m
            for m in _messages(cm.records)
            if m.startswith("middleware: stale version")
        ]
        self.assertTrue(emit)
        self.assertIn("client='some-nonsense'", emit[-1])


@override_settings(
    INERTIA_SSR_ENABLED=True,
    INERTIA_SSR_URL="ssr-url",
    INERTIA_SSR_EXCLUDE=[r"^/props/"],
)
class SSRExclusionLoggingTestCase(InertiaTestCase):
    def test_excluded_path_logs_skip_record(self):
        with self.assertLogs(_LOGGER, level="DEBUG") as cm:
            self.client.get("/props/")

        emit = [
            m
            for m in _messages(cm.records)
            if m.startswith("first-load shell: skipping SSR for path=")
        ]
        self.assertTrue(emit, msg=_messages(cm.records))
        self.assertIn("/props/", emit[-1])
        self.assertIn("^/props/", emit[-1])
