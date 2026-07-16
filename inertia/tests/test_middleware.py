from django.contrib.messages import get_messages
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpResponse
from django.test import RequestFactory, override_settings

from inertia.http import inertia_redirect
from inertia.middleware import InertiaMiddleware
from inertia.test import InertiaTestCase


class MiddlewareTestCase(InertiaTestCase):
    def test_anything(self):
        response = self.client.get("/test/")

        self.assertEqual(response.status_code, 200)

    def test_stale_versions_are_refreshed(self):
        response = self.inertia.get(
            "/empty/",
            HTTP_X_INERTIA_VERSION="some-nonsense",
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.headers["X-Inertia-Location"], "http://testserver/empty/"
        )
        # The automatic version-change 409 echoes the CURRENT server version
        # (the packaged default) so the v3.6+ client can suppress forced reloads
        # on background requests — mirrors Laravel's MiddlewareTest assertion.
        self.assertEqual(response.headers["X-Inertia-Version"], "1.0")

    def test_stale_versions_do_not_refresh_mutations(self):
        # Per the v3 protocol, the 409 + X-Inertia-Location hard reload is sent
        # only for GET requests, never for POST/PUT/PATCH/DELETE. A GET redirect
        # after a mutation still carries the version check, so the follow-up GET
        # is what triggers the 409 — not the mutation itself.
        response = self.inertia.post(
            "/redirect/",
            HTTP_X_INERTIA_VERSION="some-nonsense",
        )
        self.assertEqual(response.status_code, 302)
        self.assertNotIn("X-Inertia-Location", response.headers)

        for http_method in ["put", "patch", "delete"]:
            response = getattr(self.inertia, http_method)(
                "/redirect/",
                HTTP_X_INERTIA_VERSION="some-nonsense",
            )
            self.assertEqual(response.status_code, 303, http_method)
            self.assertNotIn("X-Inertia-Location", response.headers)

    def test_missing_version_header_is_treated_as_fresh(self):
        # An Inertia GET with no X-Inertia-Version header must render normally:
        # is_stale defaults the absent header to the server version, so the
        # request is fresh and not converted into a 409 hard reload.
        response = self.inertia.get("/empty/")

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("X-Inertia-Location", response.headers)

    def test_redirect_status(self):
        response = self.inertia.post("/redirect/")
        self.assertEqual(response.status_code, 302)

        for http_method in ["put", "patch", "delete"]:
            response = getattr(self.inertia, http_method)("/redirect/")

            self.assertEqual(response.status_code, 303)

    def test_a_request_not_from_inertia_is_ignored(self):
        response = self.client.get(
            "/empty/",
            HTTP_X_INERTIA_VERSION="some-nonsense",
        )

        self.assertEqual(response.status_code, 200)

    def test_external_redirect_status(self):
        response = self.inertia.post("/external-redirect/")
        self.assertEqual(response.status_code, 409)
        self.assertIn("X-Inertia-Location", response.headers)
        self.assertEqual("http://foobar.com/", response.headers["X-Inertia-Location"])
        # A manual location() 409 stays version-free — the discriminator the
        # v3.6+ client uses to always navigate. With the header, an async
        # request from a deploy-stale client would silently swallow this
        # real redirect instead of following it.
        self.assertNotIn("X-Inertia-Version", response.headers)


class VersionResolutionStalenessTestCase(InertiaTestCase):
    @override_settings(INERTIA_VERSION=lambda: "deploy-hash")
    def test_callable_version_matching_header_is_fresh(self):
        response = self.inertia.get(
            "/empty/",
            HTTP_X_INERTIA_VERSION="deploy-hash",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.page()["version"], "deploy-hash")

    @override_settings(INERTIA_VERSION=lambda: "deploy-hash")
    def test_callable_version_mismatched_header_forces_refresh(self):
        response = self.inertia.get(
            "/empty/",
            HTTP_X_INERTIA_VERSION="old-hash",
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.headers["X-Inertia-Location"], "http://testserver/empty/"
        )
        # We echo the CURRENT server version ("deploy-hash"), never a reflection
        # of the request's stale header ("old-hash").
        self.assertEqual(response.headers["X-Inertia-Version"], "deploy-hash")

    @override_settings(INERTIA_VERSION=42)
    def test_non_string_version_does_not_loop_against_string_header(self):
        # Regression: the X-Inertia-Version header is always a string, so an int
        # setting used to compare unequal to the matching client value (str "42"
        # != int 42), forcing a 409 hard reload on every GET. The str cast in
        # resolve_inertia_version makes the round-trip fresh again.
        response = self.inertia.get(
            "/empty/",
            HTTP_X_INERTIA_VERSION="42",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.page()["version"], "42")
        self.assertIsInstance(self.page()["version"], str)

    @override_settings(INERTIA_VERSION=None)
    def test_disabled_version_missing_header_is_fresh(self):
        # version=None resolves to "", which the v3 client treats as "no
        # versioning" and never echoes back. A header-less GET must stay fresh.
        response = self.inertia.get("/empty/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.page()["version"], "")
        self.assertNotIn("X-Inertia-Location", response.headers)

    @override_settings(INERTIA_VERSION=None)
    def test_disabled_version_stale_refresh_still_echoes_empty_header(self):
        # Pins the unconditional set: even when INERTIA_VERSION is unset (it
        # resolves to ""), the automatic 409 carries an X-Inertia-Version header
        # — present but empty — so a future truthiness guard can't sneak in.
        # Laravel emits the empty header too; the client treats empty and absent
        # identically.
        response = self.inertia.get("/empty/", HTTP_X_INERTIA_VERSION="stale")

        self.assertEqual(response.status_code, 409)
        self.assertIn("X-Inertia-Version", response.headers)
        self.assertEqual(response.headers["X-Inertia-Version"], "")


class FragmentRedirectTestCase(InertiaTestCase):
    def test_inertia_request_with_fragment_redirect_returns_409(self):
        response = self.inertia.get("/fragment-redirect/")
        self.assertEqual(response.status_code, 409)
        self.assertIn("X-Inertia-Redirect", response.headers)
        self.assertIn("#section", response.headers["X-Inertia-Redirect"])
        # An inertia_redirect() 409 stays version-free (Laravel's
        # onRedirectWithFragment sets only the redirect header) — the version
        # header is the discriminator reserved for the automatic 409.
        self.assertNotIn("X-Inertia-Version", response.headers)

    def test_non_inertia_request_with_fragment_redirect_is_left_alone(self):
        response = self.client.get("/fragment-redirect/")
        self.assertEqual(response.status_code, 302)
        self.assertNotIn("X-Inertia-Redirect", response.headers)
        self.assertIn("#section", response.headers["Location"])


class InertiaRedirectHelperTestCase(InertiaTestCase):
    def test_inertia_redirect_helper_returns_409_with_header(self):
        response = inertia_redirect("/foo#bar")
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.headers["X-Inertia-Redirect"], "/foo#bar")
        # inertia_redirect() 409s stay version-free — the X-Inertia-Version
        # discriminator is reserved for the automatic version-change 409.
        self.assertNotIn("X-Inertia-Version", response.headers)

    def test_inertia_redirect_helper_used_in_view(self):
        response = self.inertia.get("/inertia-redirect-helper/")
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.headers["X-Inertia-Redirect"], "/foo#bar")


class ForceRefreshReflashTestCase(InertiaTestCase):
    def test_force_refresh_reflashes_already_consumed_messages(self):
        # A stale-version GET is discarded in favor of a 409 hard reload. Any
        # flash messages the discarded response already consumed must be
        # reflashed (storage.used reset to False) so the follow-up reload can
        # still display them, matching Laravel's flash reflash on 409.
        request = RequestFactory().get("/empty/")
        SessionMiddleware(lambda r: HttpResponse()).process_request(request)
        MessageMiddleware(lambda r: HttpResponse()).process_request(request)
        storage = get_messages(request)
        storage.used = True

        InertiaMiddleware(lambda r: HttpResponse()).force_refresh(request)

        self.assertFalse(get_messages(request).used)

    def _request_with_session(self):
        request = RequestFactory().get("/empty/")
        SessionMiddleware(lambda r: HttpResponse()).process_request(request)
        MessageMiddleware(lambda r: HttpResponse()).process_request(request)
        return request

    def test_force_refresh_restores_flash_consumed_by_the_discarded_response(self):
        from inertia.http import INERTIA_SESSION_FLASH

        request = self._request_with_session()
        discarded = HttpResponse()
        discarded._pulled_flash = {"toast": "Pending"}

        InertiaMiddleware(lambda r: HttpResponse()).force_refresh(request, discarded)

        self.assertEqual(request.session[INERTIA_SESSION_FLASH], {"toast": "Pending"})

    def test_reflash_keeps_newer_flash_values_written_after_the_pull(self):
        from inertia.http import INERTIA_SESSION_FLASH

        request = self._request_with_session()
        request.session[INERTIA_SESSION_FLASH] = {"toast": "Newer"}
        discarded = HttpResponse()
        discarded._pulled_flash = {"toast": "Older", "banner": "Hi"}

        InertiaMiddleware(lambda r: HttpResponse()).force_refresh(request, discarded)

        self.assertEqual(
            request.session[INERTIA_SESSION_FLASH],
            {"toast": "Newer", "banner": "Hi"},
        )

    def test_reflash_discards_corrupted_current_flash_state(self):
        from inertia.http import INERTIA_SESSION_FLASH

        request = self._request_with_session()
        request.session[INERTIA_SESSION_FLASH] = "corrupted"
        discarded = HttpResponse()
        discarded._pulled_flash = {"toast": "Pending"}

        InertiaMiddleware(lambda r: HttpResponse()).force_refresh(request, discarded)

        self.assertEqual(request.session[INERTIA_SESSION_FLASH], {"toast": "Pending"})

    def test_force_refresh_restores_errors_consumed_by_the_discarded_response(self):
        from inertia.http import INERTIA_SESSION_ERRORS

        request = self._request_with_session()
        request.session[INERTIA_SESSION_ERRORS] = "corrupted"
        discarded = HttpResponse()
        discarded._pulled_errors = {"name": ["Required"]}

        InertiaMiddleware(lambda r: HttpResponse()).force_refresh(request, discarded)

        self.assertEqual(
            request.session[INERTIA_SESSION_ERRORS], {"name": ["Required"]}
        )

    def test_one_shot_history_flags_survive_the_409_refresh(self):
        from inertia.http import (
            INERTIA_SESSION_CLEAR_HISTORY,
            INERTIA_SESSION_PRESERVE_FRAGMENT,
        )

        request = self._request_with_session()
        discarded = HttpResponse()
        discarded._pulled_clear_history = True
        discarded._pulled_preserve_fragment = True

        InertiaMiddleware(lambda r: HttpResponse()).force_refresh(request, discarded)

        self.assertTrue(request.session[INERTIA_SESSION_CLEAR_HISTORY])
        self.assertTrue(request.session[INERTIA_SESSION_PRESERVE_FRAGMENT])

    def test_a_plain_response_without_stashes_reflashes_nothing(self):
        # A stale GET to a non-Inertia view discards a plain HttpResponse
        # that never pulled session state — force_refresh must not fabricate
        # flash/errors/history flags from getattr defaults.
        from inertia.http import (
            INERTIA_SESSION_CLEAR_HISTORY,
            INERTIA_SESSION_ERRORS,
            INERTIA_SESSION_FLASH,
            INERTIA_SESSION_PRESERVE_FRAGMENT,
        )

        request = self._request_with_session()
        plain = HttpResponse("not an inertia render")

        InertiaMiddleware(lambda r: HttpResponse()).force_refresh(request, plain)

        self.assertNotIn(INERTIA_SESSION_CLEAR_HISTORY, request.session)
        self.assertNotIn(INERTIA_SESSION_PRESERVE_FRAGMENT, request.session)
        self.assertNotIn(INERTIA_SESSION_FLASH, request.session)
        self.assertNotIn(INERTIA_SESSION_ERRORS, request.session)


class HistoryFlagsStaleRefreshEndToEndTestCase(InertiaTestCase):
    def test_clear_history_flag_survives_a_stale_version_refresh(self):
        from inertia.http import INERTIA_SESSION_CLEAR_HISTORY

        session = self.inertia.session
        session[INERTIA_SESSION_CLEAR_HISTORY] = True
        session.save()

        stale = self.inertia.get("/empty/", HTTP_X_INERTIA_VERSION="stale")

        self.assertEqual(stale.status_code, 409)
        self.assertTrue(self.inertia.session[INERTIA_SESSION_CLEAR_HISTORY])

        fresh = self.inertia.get("/empty/")

        self.assertTrue(fresh.json()["clearHistory"])

    def test_preserve_fragment_flag_survives_a_stale_version_refresh(self):
        from inertia.http import INERTIA_SESSION_PRESERVE_FRAGMENT

        session = self.inertia.session
        session[INERTIA_SESSION_PRESERVE_FRAGMENT] = True
        session.save()

        stale = self.inertia.get("/empty/", HTTP_X_INERTIA_VERSION="stale")

        self.assertEqual(stale.status_code, 409)
        self.assertTrue(self.inertia.session[INERTIA_SESSION_PRESERVE_FRAGMENT])

        fresh = self.inertia.get("/empty/")

        self.assertTrue(fresh.json()["preserveFragment"])
