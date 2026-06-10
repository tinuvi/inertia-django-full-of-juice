"""Tests for the v3 Precognition decorator (`inertia.precognition`).

Pins the wire contract from the v3 protocol §Precognition: request headers
``Precognition`` / ``Precognition-Validate-Only``, the 204 +
``Precognition-Success: true`` success shape, the 422 ``{message, errors}``
failure shape, the ``Precognition: true`` echo the client hard-requires,
and ``Vary: Precognition`` on every response of a wrapped view.
"""

from __future__ import annotations

from json import dumps

from inertia.precognition import is_precognitive, validate_only_keys
from inertia.test import InertiaTestCase

VALID = {"name": "ok", "email": "a@b.com", "age": 30}


def vary_directives(response) -> list[str]:
    return [d.strip() for d in response.headers.get("Vary", "").split(",")]


class PrecognitionSuccessTestCase(InertiaTestCase):
    def test_valid_json_body_returns_204_with_success_headers(self) -> None:
        response = self.client.post(
            "/precog/",
            data=dumps(VALID),
            content_type="application/json",
            HTTP_PRECOGNITION="true",
        )

        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b"")
        self.assertEqual(response.headers["Precognition"], "true")
        self.assertEqual(response.headers["Precognition-Success"], "true")
        self.assertIn("Precognition", vary_directives(response))

    def test_view_body_never_runs_for_precognitive_requests(self) -> None:
        response = self.client.post(
            "/precog/",
            data=dumps(VALID),
            content_type="application/json",
            HTTP_PRECOGNITION="true",
        )

        self.assertEqual(response.status_code, 204)
        self.assertIsNone(self.mock_render.call_args)

    def test_valid_multipart_post_returns_204(self) -> None:
        response = self.client.post(
            "/precog/",
            data={"name": "ok", "email": "a@b.com", "age": "30"},
            HTTP_PRECOGNITION="true",
        )

        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.headers["Precognition-Success"], "true")

    def test_valid_urlencoded_post_returns_204(self) -> None:
        response = self.client.post(
            "/precog/",
            data="name=ok&email=a%40b.com&age=30",
            content_type="application/x-www-form-urlencoded",
            HTTP_PRECOGNITION="true",
        )

        self.assertEqual(response.status_code, 204)

    def test_get_requests_validate_query_params(self) -> None:
        response = self.client.get(
            "/precog/",
            {"name": "ok", "email": "a@b.com", "age": "30"},
            HTTP_PRECOGNITION="true",
        )

        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.headers["Precognition-Success"], "true")


class PrecognitionFailureTestCase(InertiaTestCase):
    def test_invalid_body_returns_422_with_laravel_error_shape(self) -> None:
        response = self.client.post(
            "/precog/",
            data=dumps({"name": "toolongname", "email": "nope", "age": 10}),
            content_type="application/json",
            HTTP_PRECOGNITION="true",
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.headers["Precognition"], "true")
        self.assertNotIn("Precognition-Success", response.headers)
        body = response.json()
        self.assertEqual(body["message"], "The given data was invalid.")
        self.assertEqual(sorted(body["errors"].keys()), ["age", "email", "name"])
        for messages in body["errors"].values():
            self.assertIsInstance(messages, list)

    def test_empty_json_body_fails_required_validation(self) -> None:
        response = self.client.post(
            "/precog/",
            data="",
            content_type="application/json",
            HTTP_PRECOGNITION="true",
        )

        self.assertEqual(response.status_code, 422)

    def test_non_field_errors_from_clean_are_reported(self) -> None:
        response = self.client.post(
            "/precog/",
            data=dumps({"name": "admin", "email": "a@b.com", "age": 30}),
            content_type="application/json",
            HTTP_PRECOGNITION="true",
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["errors"]["__all__"], ["Reserved name"])

    def test_malformed_json_body_returns_400_with_precognition_header(self) -> None:
        response = self.client.post(
            "/precog/",
            data="{nope",
            content_type="application/json",
            HTTP_PRECOGNITION="true",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.headers["Precognition"], "true")
        self.assertEqual(response.json(), {"message": "Malformed request body."})

    def test_non_object_json_body_returns_400(self) -> None:
        response = self.client.post(
            "/precog/",
            data=dumps(["not", "an", "object"]),
            content_type="application/json",
            HTTP_PRECOGNITION="true",
        )

        self.assertEqual(response.status_code, 400)


class ValidateOnlyTestCase(InertiaTestCase):
    def test_only_listed_fields_are_validated(self) -> None:
        response = self.client.post(
            "/precog/",
            data=dumps({"email": "nope"}),
            content_type="application/json",
            HTTP_PRECOGNITION="true",
            HTTP_PRECOGNITION_VALIDATE_ONLY="email",
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(sorted(response.json()["errors"].keys()), ["email"])

    def test_valid_subset_returns_204_even_with_other_fields_missing(self) -> None:
        response = self.client.post(
            "/precog/",
            data=dumps({"email": "a@b.com"}),
            content_type="application/json",
            HTTP_PRECOGNITION="true",
            HTTP_PRECOGNITION_VALIDATE_ONLY="email",
        )

        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.headers["Precognition-Success"], "true")

    def test_comma_separated_list_validates_each_field(self) -> None:
        response = self.client.post(
            "/precog/",
            data=dumps({"email": "nope", "age": 10}),
            content_type="application/json",
            HTTP_PRECOGNITION="true",
            HTTP_PRECOGNITION_VALIDATE_ONLY="email,age",
        )

        self.assertEqual(sorted(response.json()["errors"].keys()), ["age", "email"])

    def test_wildcard_matches_one_dot_segment(self) -> None:
        response = self.client.post(
            "/precog/",
            data=dumps({"email": "nope", "name": ""}),
            content_type="application/json",
            HTTP_PRECOGNITION="true",
            HTTP_PRECOGNITION_VALIDATE_ONLY="*",
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(
            sorted(response.json()["errors"].keys()), ["age", "email", "name"]
        )


class PrecognitionPassThroughTestCase(InertiaTestCase):
    def test_non_precognitive_requests_run_the_view(self) -> None:
        response = self.inertia.post(
            "/precog/", data=dumps({}), content_type="application/json"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["props"]["submitted"], True)

    def test_pass_through_responses_vary_on_precognition(self) -> None:
        response = self.inertia.get("/precog/")

        self.assertIn("Precognition", vary_directives(response))

    def test_header_value_must_be_exactly_true(self) -> None:
        response = self.inertia.get("/precog/", HTTP_PRECOGNITION="1")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["props"]["submitted"], True)


class AsyncViewSupportTestCase(InertiaTestCase):
    def test_precognitive_request_short_circuits_an_async_view(self) -> None:
        response = self.client.post(
            "/precog-async/",
            data=dumps(VALID),
            content_type="application/json",
            HTTP_PRECOGNITION="true",
        )

        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.headers["Precognition-Success"], "true")

    def test_async_pass_through_runs_the_view_and_varies(self) -> None:
        response = self.client.get("/precog-async/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"async ok")
        self.assertIn("Precognition", vary_directives(response))


class NonPostBodyParsingTestCase(InertiaTestCase):
    """The v3 client sends the form's real method — PUT/PATCH bodies must be
    parsed by the decorator itself since Django only populates ``request.POST``
    for POST requests."""

    def test_put_json_body_is_validated(self) -> None:
        response = self.client.put(
            "/precog/",
            data=dumps(VALID),
            content_type="application/json",
            HTTP_PRECOGNITION="true",
        )

        self.assertEqual(response.status_code, 204)

    def test_put_empty_json_body_fails_required_validation(self) -> None:
        response = self.client.put(
            "/precog/",
            data="",
            content_type="application/json",
            HTTP_PRECOGNITION="true",
        )

        self.assertEqual(response.status_code, 422)

    def test_put_urlencoded_body_is_parsed_into_a_querydict(self) -> None:
        response = self.client.put(
            "/precog/",
            data="name=ok&email=a%40b.com&age=30",
            content_type="application/x-www-form-urlencoded",
            HTTP_PRECOGNITION="true",
        )

        self.assertEqual(response.status_code, 204)

    def test_put_multipart_body_is_parsed_with_the_multipart_parser(self) -> None:
        from django.test.client import MULTIPART_CONTENT, encode_multipart

        response = self.client.put(
            "/precog/",
            data=encode_multipart(
                "BoUnDaRyStRiNg", {"name": "ok", "email": "a@b.com", "age": "30"}
            ),
            content_type=MULTIPART_CONTENT,
            HTTP_PRECOGNITION="true",
        )

        self.assertEqual(response.status_code, 204)

    def test_delete_requests_validate_query_params(self) -> None:
        response = self.client.delete(
            "/precog/?name=ok&email=a%40b.com&age=30",
            HTTP_PRECOGNITION="true",
        )

        self.assertEqual(response.status_code, 204)

    def test_unknown_content_type_on_put_validates_an_empty_payload(self) -> None:
        response = self.client.put(
            "/precog/",
            data="whatever",
            content_type="text/plain",
            HTTP_PRECOGNITION="true",
        )

        self.assertEqual(response.status_code, 422)

    def test_unknown_content_type_on_post_falls_back_to_request_post(self) -> None:
        response = self.client.post(
            "/precog/",
            data="whatever",
            content_type="text/plain",
            HTTP_PRECOGNITION="true",
        )

        self.assertEqual(response.status_code, 422)


class PrecognitionHelpersTestCase(InertiaTestCase):
    def test_is_precognitive_and_validate_only_keys(self) -> None:
        from django.test import RequestFactory

        factory = RequestFactory()
        plain = factory.get("/")
        precog = factory.get(
            "/",
            HTTP_PRECOGNITION="true",
            HTTP_PRECOGNITION_VALIDATE_ONLY="email,name",
        )

        self.assertFalse(is_precognitive(plain))
        self.assertTrue(is_precognitive(precog))
        self.assertEqual(validate_only_keys(plain), [])
        self.assertEqual(validate_only_keys(precog), ["email", "name"])

    def test_uploaded_files_are_forwarded_into_the_form(self) -> None:
        # Kills the `files=files or None` → `files=None` forwarding mutants:
        # a FileField only validates when request.FILES reaches the form.
        from django.core.files.uploadedfile import SimpleUploadedFile

        response = self.client.post(
            "/precog-upload/",
            data={"avatar": SimpleUploadedFile("a.txt", b"hello")},
            HTTP_PRECOGNITION="true",
        )

        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.headers["Precognition-Success"], "true")

    def test_missing_upload_still_fails_required_validation(self) -> None:
        response = self.client.post(
            "/precog-upload/",
            data={},
            HTTP_PRECOGNITION="true",
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(sorted(response.json()["errors"].keys()), ["avatar"])

    def test_missing_request_method_defaults_to_get_semantics(self) -> None:
        # `request.method` is None only for hand-built requests; the parser
        # must still take the GET branch (query params), not the body path.
        from django.test import RequestFactory

        from inertia.precognition import _parse_request_data

        request = RequestFactory().get("/?name=ok")
        request.method = None

        data, files = _parse_request_data(request)

        self.assertEqual(data.get("name"), "ok")
        self.assertIsNone(files)

    def test_truly_empty_json_body_parses_to_an_empty_payload(self) -> None:
        # The test client drops the Content-Type header for falsy bodies, so
        # the empty-body guard is pinned directly: a zero-length body with a
        # JSON content type must validate an empty payload, not 400.
        from django.test import RequestFactory

        from inertia.precognition import _parse_request_data

        request = RequestFactory().post("/", data="x", content_type="application/json")
        request._body = b""

        data, files = _parse_request_data(request)

        self.assertEqual(data, {})
        self.assertIsNone(files)
