import json
import os
import socket
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from unittest.mock import Mock, patch

import requests
from django.test import override_settings

from inertia.test import InertiaTestCase, inertia_div, inertia_page


@override_settings(
    INERTIA_SSR_ENABLED=True,
    INERTIA_SSR_URL="ssr-url",
    INERTIA_VERSION="1.0",
)
class SSRTestCase(InertiaTestCase):
    @patch("inertia.http.requests")
    def test_it_returns_ssr_calls(self, mock_request):
        mock_response = Mock()
        mock_response.json.return_value = {
            "body": "<div>Body Works</div>",
            "head": "<title>Head works</title>",
        }

        mock_request.post.return_value = mock_response

        response = self.client.get("/props/")

        mock_request.post.assert_called_once_with(
            "ssr-url/render",
            data=json.dumps(
                inertia_page("props", props={"name": "Brandon", "sport": "Hockey"})
            ),
            headers={"Content-Type": "application/json"},
            timeout=5.0,
        )
        self.assertTemplateUsed("inertia_ssr.html")
        self.assertContains(response, "<div>Body Works</div>")
        self.assertContains(response, "head--<title>Head works</title>--head")

    @override_settings(INERTIA_SSR_TIMEOUT=(1.5, 10))
    @patch("inertia.http.requests")
    def test_it_passes_the_configured_timeout_verbatim(self, mock_requests):
        mock_requests.post.return_value = _ssr_body()

        self.client.get("/props/")

        self.assertEqual(mock_requests.post.call_args.kwargs["timeout"], (1.5, 10))

    @override_settings(INERTIA_SSR_TIMEOUT=None)
    @patch("inertia.http.requests")
    def test_it_passes_none_to_opt_out_of_the_timeout(self, mock_requests):
        mock_requests.post.return_value = _ssr_body()

        self.client.get("/props/")

        self.assertIsNone(mock_requests.post.call_args.kwargs["timeout"])

    @patch("inertia.http.requests")
    def test_it_returns_ssr_calls_with_template_data(self, mock_request):
        mock_response = Mock()
        mock_response.json.return_value = {
            "body": "<div>Body Works</div>",
            "head": "<title>Head works</title>",
        }

        mock_request.post.return_value = mock_response

        response = self.client.get("/template_data/")

        self.assertTemplateUsed("inertia_ssr.html")
        self.assertContains(response, "<div>Body Works</div>")
        self.assertContains(response, "head--<title>Head works</title>--head")
        self.assertContains(response, "Brian, Basketball")

    @patch("inertia.http.requests")
    def test_it_uses_inertia_if_inertia_requests_are_made(self, mock_requests):
        response = self.inertia.get("/props/")

        mock_requests.post.assert_not_called()
        self.assertJSONResponse(
            response,
            inertia_page("props", props={"name": "Brandon", "sport": "Hockey"}),
        )

    @patch("inertia.http.requests")
    def test_it_fallsback_on_failure(self, mock_requests):
        def uh_oh(*args, **kwargs):
            raise ValueError()  # SSR errors are logged and fall back to client-side rendering

        mock_response = Mock()
        mock_response.raise_for_status.side_effect = uh_oh
        mock_requests.post.return_value = mock_response

        response = self.client.get("/props/")
        self.assertContains(
            response, inertia_div("props", props={"name": "Brandon", "sport": "Hockey"})
        )

    @patch("inertia.http._logger")
    @patch("inertia.http.requests")
    def test_it_logs_exception_on_ssr_failure(self, mock_requests, mock_logger):
        error = ValueError("SSR rendering failed")

        mock_response = Mock()
        mock_response.raise_for_status.side_effect = error
        mock_requests.post.return_value = mock_response

        self.client.get("/props/")

        mock_logger.exception.assert_called_once_with("SSR render request failed")

    @patch("inertia.http._logger")
    @patch("inertia.http.requests")
    def test_it_fallsback_on_timeout(self, mock_requests, mock_logger):
        mock_requests.post.side_effect = requests.exceptions.ReadTimeout()

        response = self.client.get("/props/")

        self.assertTemplateUsed(response, "inertia.html")
        self.assertContains(
            response, inertia_div("props", props={"name": "Brandon", "sport": "Hockey"})
        )
        mock_logger.exception.assert_called_once_with("SSR render request failed")

    @patch("inertia.http.requests")
    def test_it_fallsback_on_connection_error(self, mock_requests):
        mock_requests.post.side_effect = requests.exceptions.ConnectionError()

        response = self.client.get("/props/")

        self.assertTemplateUsed(response, "inertia.html")

    @patch("inertia.http.requests")
    def test_it_fallsback_on_http_error(self, mock_requests):
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError()
        mock_requests.post.return_value = mock_response

        response = self.client.get("/props/")

        self.assertTemplateUsed(response, "inertia.html")

    @patch("inertia.http.requests")
    def test_it_fallsback_on_a_body_that_is_not_json(self, mock_requests):
        mock_response = Mock()
        mock_response.json.side_effect = requests.exceptions.JSONDecodeError(
            "Expecting value", "<html>502 Bad Gateway</html>", 0
        )
        mock_requests.post.return_value = mock_response

        response = self.client.get("/props/")

        self.assertTemplateUsed(response, "inertia.html")

    @patch("inertia.http.requests")
    def test_it_fallsback_on_pathologically_nested_json(self, mock_requests):
        # A real ``Response``: ``json()`` itself hits the recursion limit.
        nested = requests.models.Response()
        nested.status_code = 200
        nested.encoding = "utf-8"
        nested._content = b"[" * 100_000 + b"]" * 100_000
        mock_requests.post.return_value = nested

        response = self.client.get("/props/")

        self.assertTemplateUsed(response, "inertia.html")

    @patch("inertia.http.requests")
    def test_it_fallsback_on_a_timeout_the_platform_clock_cannot_represent(
        self, mock_requests
    ):
        mock_requests.post.side_effect = OverflowError(
            "timestamp out of range for platform time_t"
        )

        response = self.client.get("/props/")

        self.assertTemplateUsed(response, "inertia.html")

    @patch("inertia.http._logger")
    @patch("inertia.http.requests")
    def test_it_fallsback_on_a_non_object_json_body(self, mock_requests, mock_logger):
        # The Vite dev SSR endpoint answers 200 ``null`` while it warms up.
        mock_response = Mock()
        mock_response.json.return_value = None
        mock_requests.post.return_value = mock_response

        response = self.client.get("/props/")

        self.assertTemplateUsed(response, "inertia.html")
        self.assertContains(
            response, inertia_div("props", props={"name": "Brandon", "sport": "Hockey"})
        )
        mock_logger.error.assert_called_once_with(
            "SSR render request failed: the response has no rendered body "
            "(component=%r)",
            "TestComponent",
        )

    def test_it_fallsback_on_a_response_without_rendered_markup(self):
        # A 2xx whose payload carries no usable ``body`` would render a page
        # without the app root, so the client could never boot: it must fall
        # back to the client shell exactly like a failed render.
        for payload in (
            {},
            {"head": ["<title>Head works</title>"]},
            {"head": [], "body": ""},
            {"head": [], "body": "   \n"},
            {"head": [], "body": None},
            {"head": [], "body": ["<div>not a string</div>"]},
            [],
            "<div>Body Works</div>",
        ):
            with (
                self.subTest(payload=payload),
                patch("inertia.http.requests") as mock_requests,
                patch("inertia.http._logger") as mock_logger,
            ):
                mock_response = Mock()
                mock_response.json.return_value = payload
                mock_requests.post.return_value = mock_response

                response = self.client.get("/props/")

                self.assertEqual(response.status_code, 200)
                self.assertContains(
                    response,
                    inertia_div("props", props={"name": "Brandon", "sport": "Hockey"}),
                )
                self.assertNotContains(
                    response, "head--<title>Head works</title>--head"
                )
                mock_logger.error.assert_called_once()

    @patch("inertia.http._logger")
    @patch("inertia.http.requests")
    def test_it_propagates_exceptions_unrelated_to_the_render_call(
        self, mock_requests, mock_logger
    ):
        # A per-request deadline (gunicorn+gevent's ``gevent.Timeout(n,
        # exception=SomeError)`` with an ``Exception`` subclass) can fire while
        # the render call waits. It must reach the application, not be turned
        # into a 200 client shell.
        mock_requests.post.side_effect = _DeadlineExceededError()

        with self.assertRaises(_DeadlineExceededError):
            self.client.get("/props/")

        mock_logger.exception.assert_not_called()


class _DeadlineExceededError(Exception):
    pass


@contextmanager
def _unresponsive_ssr_server(give_up_after: float = 10.0) -> Iterator[str]:
    """A listening socket that never answers: the TCP handshake completes via the
    kernel backlog, the request bytes are buffered, and no response ever comes —
    a hung SSR service rather than a dead one (which would refuse at once).

    Watchdog: if the render call ever stops honoring its timeout, closing the
    listener after ``give_up_after`` seconds resets the pending connection, so
    the test fails on its timing assertion instead of hanging the suite."""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("127.0.0.1", 0))
    server.listen(8)
    watchdog = threading.Timer(give_up_after, server.close)
    watchdog.daemon = True
    watchdog.start()
    try:
        yield f"http://127.0.0.1:{server.getsockname()[1]}"
    finally:
        watchdog.cancel()
        server.close()


# A proxy from the environment would answer in place of the stub.
@patch.dict(os.environ, {"NO_PROXY": "127.0.0.1", "no_proxy": "127.0.0.1"})
@override_settings(INERTIA_SSR_ENABLED=True, INERTIA_VERSION="1.0")
class SSRTimeoutRealSocketTestCase(InertiaTestCase):
    """Unmocked ``requests`` against a hung SSR service: proves the timeout is
    honored on the wire, not just passed as a keyword argument."""

    def test_a_hung_ssr_service_falls_back_to_the_client_shell(self):
        with (
            _unresponsive_ssr_server() as url,
            override_settings(INERTIA_SSR_URL=url, INERTIA_SSR_TIMEOUT=0.2),
            self.assertLogs("inertia_django_full_of_juice", "ERROR") as logs,
        ):
            started = time.monotonic()
            response = self.client.get("/props/")
            elapsed = time.monotonic() - started

        self.assertTemplateUsed(response, "inertia.html")
        self.assertContains(
            response, inertia_div("props", props={"name": "Brandon", "sport": "Hockey"})
        )
        self.assertLess(elapsed, 5)
        self.assertIn("SSR render request failed", logs.output[0])
        self.assertIn("ReadTimeout", logs.output[0])

    def test_a_malformed_timeout_falls_back(self):
        # Why ``inertia.E002`` exists: urllib3 rejects the value with ValueError
        # on every call, so SSR is silently disabled rather than failing loudly.
        with (
            _unresponsive_ssr_server() as url,
            override_settings(INERTIA_SSR_URL=url, INERTIA_SSR_TIMEOUT="4"),
            self.assertLogs("inertia_django_full_of_juice", "ERROR") as logs,
        ):
            response = self.client.get("/props/")

        self.assertTemplateUsed(response, "inertia.html")
        self.assertIn("ValueError", logs.output[0])

    def test_an_infinite_timeout_falls_back_instead_of_failing_the_request(self):
        # ``inf`` passes urllib3's validation, then overflows the platform clock
        # (``inertia.E002`` rejects it at startup; this is the runtime backstop).
        with (
            _unresponsive_ssr_server() as url,
            override_settings(INERTIA_SSR_URL=url, INERTIA_SSR_TIMEOUT=float("inf")),
            self.assertLogs("inertia_django_full_of_juice", "ERROR") as logs,
        ):
            response = self.client.get("/props/")

        self.assertTemplateUsed(response, "inertia.html")
        self.assertIn("OverflowError", logs.output[0])

    def test_a_missing_ca_bundle_falls_back(self):
        # requests raises a plain ``OSError`` (not a ``RequestException``) for an
        # https URL whose CA bundle path does not exist, before connecting.
        with (
            _unresponsive_ssr_server() as url,
            patch.dict(os.environ, {"REQUESTS_CA_BUNDLE": "/nonexistent/ca.pem"}),
            override_settings(INERTIA_SSR_URL=url.replace("http://", "https://")),
            self.assertLogs("inertia_django_full_of_juice", "ERROR") as logs,
        ):
            response = self.client.get("/props/")

        self.assertTemplateUsed(response, "inertia.html")
        self.assertIn("OSError", logs.output[0])
        self.assertIn("CA certificate bundle", logs.output[0])


def _ssr_body() -> Mock:
    mock_response = Mock()
    mock_response.json.return_value = {
        "body": "<div>Body Works</div>",
        "head": "<title>Head works</title>",
    }
    return mock_response


@override_settings(
    INERTIA_SSR_ENABLED=True,
    INERTIA_SSR_URL="ssr-url",
    INERTIA_VERSION="1.0",
)
class SSRExcludeTestCase(InertiaTestCase):
    """``INERTIA_SSR_EXCLUDE`` — per-path opt-out from server-side rendering.

    Mirrors Inertia v3's "Excluding Routes from SSR". A matching
    ``request.path`` skips the SSR render call and falls back to the same
    inline-JSON client shell the library already serves when SSR is off or
    fails, matching Laravel's gateway returning ``null`` for an excluded path.
    """

    @override_settings(INERTIA_SSR_EXCLUDE=[r"^/props/"])
    @patch("inertia.http.requests")
    def test_excluded_path_skips_ssr_and_falls_back_to_client_shell(
        self, mock_requests
    ):
        response = self.client.get("/props/")

        mock_requests.post.assert_not_called()
        self.assertTemplateUsed("inertia.html")
        self.assertContains(
            response,
            inertia_div("props", props={"name": "Brandon", "sport": "Hockey"}),
        )

    @override_settings(INERTIA_SSR_EXCLUDE=[r"^/props/"])
    @patch("inertia.http.requests")
    def test_non_matching_path_still_renders_via_ssr(self, mock_requests):
        mock_requests.post.return_value = _ssr_body()

        response = self.client.get("/template_data/")

        mock_requests.post.assert_called_once()
        self.assertTemplateUsed("inertia_ssr.html")
        self.assertContains(response, "<div>Body Works</div>")

    @override_settings(INERTIA_SSR_EXCLUDE=[r"^/nope/", r"^/props/"])
    @patch("inertia.http.requests")
    def test_any_matching_pattern_excludes(self, mock_requests):
        response = self.client.get("/props/")

        mock_requests.post.assert_not_called()
        self.assertContains(
            response,
            inertia_div("props", props={"name": "Brandon", "sport": "Hockey"}),
        )

    @override_settings(INERTIA_SSR_EXCLUDE=[r"props"])
    @patch("inertia.http.requests")
    def test_patterns_are_searched_not_anchored(self, mock_requests):
        # re.search semantics — an unanchored substring pattern still matches,
        # matching Django's SECURE_REDIRECT_EXEMPT (search, not match).
        response = self.client.get("/props/")

        mock_requests.post.assert_not_called()
        self.assertContains(
            response,
            inertia_div("props", props={"name": "Brandon", "sport": "Hockey"}),
        )

    @patch("inertia.http.requests")
    def test_empty_exclude_default_still_renders_via_ssr(self, mock_requests):
        # No INERTIA_SSR_EXCLUDE override → default [] → SSR proceeds untouched.
        mock_requests.post.return_value = _ssr_body()

        response = self.client.get("/props/")

        mock_requests.post.assert_called_once()
        self.assertTemplateUsed("inertia_ssr.html")
        self.assertContains(response, "<div>Body Works</div>")
