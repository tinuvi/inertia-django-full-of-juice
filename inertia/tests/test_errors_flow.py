"""Tests for the built-in validation-errors flow (`flash_errors` / `redirect_back`).

Mirrors Laravel's redirect-back-with-errors loop: errors are flashed to the
session, the next render flattens each field to its first message, nests
under ``X-Inertia-Error-Bag`` when present, and consumes the bag one-shot.
"""

from __future__ import annotations

from inertia.http import INERTIA_SESSION_ERRORS
from inertia.test import InertiaTestCase, inertia_page


class BackRedirectTestCase(InertiaTestCase):
    def test_back_redirects_to_a_same_host_referer(self) -> None:
        response = self.inertia.get(
            "/back-plain/", HTTP_REFERER="http://testserver/empty/"
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "http://testserver/empty/")

    def test_back_without_referer_uses_the_fallback(self) -> None:
        response = self.inertia.get("/back-plain/")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/empty/")

    def test_back_without_referer_resolves_a_url_name_fallback(self) -> None:
        # ``fallback`` runs through django.shortcuts.resolve_url, so a URL
        # name resolves to its path.
        response = self.inertia.get("/back-named-fallback/")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/empty/")

    def test_back_referer_wins_over_a_url_name_fallback(self) -> None:
        response = self.inertia.get(
            "/back-named-fallback/", HTTP_REFERER="http://testserver/props/"
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "http://testserver/props/")

    def test_back_rejects_a_cross_host_referer(self) -> None:
        response = self.inertia.get(
            "/back-plain/", HTTP_REFERER="https://evil.example.com/phish"
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/empty/")

    def test_back_rejects_an_http_referer_on_a_secure_request(self) -> None:
        # url_has_allowed_host_and_scheme must receive require_https=True for
        # secure requests, so a downgrade-to-http referer falls back.
        response = self.inertia.get(
            "/back-plain/",
            HTTP_REFERER="http://testserver/empty/",
            secure=True,
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/empty/")


class ErrorsFlowTestCase(InertiaTestCase):
    def test_back_with_dict_errors_renders_first_message_per_field(self) -> None:
        redirect = self.inertia.get(
            "/back-dict-errors/", HTTP_REFERER="http://testserver/empty/"
        )
        self.assertEqual(redirect.status_code, 302)

        response = self.inertia.get("/empty/")

        self.assertJSONResponse(
            response,
            inertia_page(
                "empty", props={"errors": {"name": "Required", "email": "Invalid"}}
            ),
        )

    def test_back_with_a_bound_form_uses_django_error_messages(self) -> None:
        self.inertia.get("/back-form-errors/")

        props = self.inertia.get("/empty/").json()["props"]

        self.assertEqual(
            props["errors"],
            {
                "name": "Ensure this value has at most 10 characters (it has 20).",
                "email": "Enter a valid email address.",
            },
        )

    def test_session_errors_are_one_shot(self) -> None:
        self.inertia.get("/back-dict-errors/")

        self.inertia.get("/empty/")
        response = self.inertia.get("/empty/")

        self.assertJSONResponse(response, inertia_page("empty"))
        self.assertNotIn(INERTIA_SESSION_ERRORS, self.inertia.session)

    def test_error_bag_header_nests_the_errors(self) -> None:
        self.inertia.get("/flash-errors-only/")

        response = self.inertia.get("/empty/", HTTP_X_INERTIA_ERROR_BAG="newsletter")

        self.assertJSONResponse(
            response,
            inertia_page(
                "empty", props={"errors": {"newsletter": {"name": "Required"}}}
            ),
        )

    def test_flash_errors_calls_replace_across_requests(self) -> None:
        # REPLACE semantics (Laravel's ``withErrors``): the second flash wins
        # wholesale. The first call stored only ``name``; the second stores
        # ``name`` + ``email`` — and a stale field from the first call must
        # never resurface.
        self.inertia.get("/back-dict-errors/")
        self.inertia.get("/flash-errors-only/")

        props = self.inertia.get("/empty/").json()["props"]

        self.assertEqual(props["errors"], {"name": "Required"})
        self.assertNotIn("email", props["errors"])

    def test_view_provided_errors_win_but_session_errors_still_age_out(self) -> None:
        self.inertia.get("/flash-errors-only/")

        response = self.inertia.get("/errors-per-render/")

        self.assertEqual(response.json()["props"]["errors"], {"sport": "Invalid"})
        self.assertNotIn(INERTIA_SESSION_ERRORS, self.inertia.session)

    def test_shared_errors_win_over_session_errors(self) -> None:
        self.inertia.get("/flash-errors-only/")

        response = self.inertia.get("/errors-share/")

        self.assertEqual(response.json()["props"]["errors"], {"name": "Required"})

    def test_non_dict_session_errors_raise_type_error(self) -> None:
        session = self.inertia.session
        session[INERTIA_SESSION_ERRORS] = "corrupted"
        session.save()

        with self.assertRaises(TypeError):
            self.inertia.get("/empty/")

    def test_hand_written_string_values_pass_through_unflattened(self) -> None:
        # Sessions written without flash_errors() may hold bare strings; the
        # flattener must pass them through whole, not slice the first char.
        session = self.inertia.session
        session[INERTIA_SESSION_ERRORS] = {"name": "Required"}
        session.save()

        props = self.inertia.get("/empty/").json()["props"]

        self.assertEqual(props["errors"], {"name": "Required"})

    def test_empty_list_values_pass_through_as_empty(self) -> None:
        session = self.inertia.session
        session[INERTIA_SESSION_ERRORS] = {"name": []}
        session.save()

        props = self.inertia.get("/empty/").json()["props"]

        self.assertEqual(props["errors"], {"name": []})


class FlashErrorsNormalizationTestCase(InertiaTestCase):
    def _request_with_session(self):
        from django.contrib.sessions.middleware import SessionMiddleware
        from django.http import HttpResponse
        from django.test import RequestFactory

        request = RequestFactory().get("/empty/")
        SessionMiddleware(lambda r: HttpResponse()).process_request(request)
        return request

    def test_scalar_and_tuple_values_are_normalized_to_string_lists(self) -> None:
        from inertia import flash_errors
        from inertia.http import INERTIA_SESSION_ERRORS

        request = self._request_with_session()

        flash_errors(request, {"age": 42, "name": ("Required", "Too short")})

        self.assertEqual(
            request.session[INERTIA_SESSION_ERRORS],
            {"age": ["42"], "name": ["Required", "Too short"]},
        )

    def test_validation_error_values_flatten_to_their_messages(self) -> None:
        # The add_error normalization idiom: a ValidationError value must
        # yield its message strings, not "['Nope']"-style repr noise.
        from django.core.exceptions import ValidationError

        from inertia import flash_errors
        from inertia.http import INERTIA_SESSION_ERRORS

        request = self._request_with_session()

        flash_errors(request, {"reason": ValidationError("Nope")})

        self.assertEqual(request.session[INERTIA_SESSION_ERRORS], {"reason": ["Nope"]})

    def test_empty_list_values_are_dropped_at_store_time(self) -> None:
        from inertia import flash_errors
        from inertia.http import INERTIA_SESSION_ERRORS

        request = self._request_with_session()

        flash_errors(request, {"name": [], "kept": "Required"})

        self.assertEqual(
            request.session[INERTIA_SESSION_ERRORS], {"kept": ["Required"]}
        )

    def test_flash_errors_replaces_existing_session_state(self) -> None:
        # Each call REPLACES the bag wholesale — even hand-corrupted session
        # state is simply overwritten (no TypeError, no merge).
        from inertia import flash_errors
        from inertia.http import INERTIA_SESSION_ERRORS

        request = self._request_with_session()
        request.session[INERTIA_SESSION_ERRORS] = "corrupted"

        flash_errors(request, {"name": "Required"})

        self.assertEqual(
            request.session[INERTIA_SESSION_ERRORS], {"name": ["Required"]}
        )


class ErrorsForceRefreshReflashTestCase(InertiaTestCase):
    def test_pending_errors_survive_the_409_stale_version_refresh(self) -> None:
        self.inertia.get("/flash-errors-only/")

        stale = self.inertia.get("/empty/", HTTP_X_INERTIA_VERSION="stale")

        self.assertEqual(stale.status_code, 409)
        self.assertEqual(
            self.inertia.session[INERTIA_SESSION_ERRORS], {"name": ["Required"]}
        )

        fresh = self.inertia.get("/empty/")

        self.assertEqual(fresh.json()["props"]["errors"], {"name": "Required"})
