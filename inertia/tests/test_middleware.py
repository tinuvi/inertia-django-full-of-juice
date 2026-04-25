from inertia.http import inertia_redirect
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


class FragmentRedirectTestCase(InertiaTestCase):
    def test_inertia_request_with_fragment_redirect_returns_409(self):
        response = self.inertia.get("/fragment-redirect/")
        self.assertEqual(response.status_code, 409)
        self.assertIn("X-Inertia-Redirect", response.headers)
        self.assertIn("#section", response.headers["X-Inertia-Redirect"])

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

    def test_inertia_redirect_helper_used_in_view(self):
        response = self.inertia.get("/inertia-redirect-helper/")
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.headers["X-Inertia-Redirect"], "/foo#bar")
