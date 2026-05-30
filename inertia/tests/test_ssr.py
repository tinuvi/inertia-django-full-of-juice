import json
from unittest.mock import Mock, patch

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
        )
        self.assertTemplateUsed("inertia_ssr.html")
        self.assertContains(response, "<div>Body Works</div>")
        self.assertContains(response, "head--<title>Head works</title>--head")

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
