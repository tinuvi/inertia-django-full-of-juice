"""Mutmut kill tests for ``inertia/http.py``.

These tests target surviving mutants that are not exercised by the
broader rendering / history / SSR suites. They focus on:

* Wire-protocol header names and values produced by
  :class:`InertiaResponse`, :func:`location`, and :func:`inertia_redirect`.
* The HTML-safe escape applied to inline page JSON in
  :meth:`BaseInertiaResponseMixin.build_first_load_context_and_template`.
* Comma-separated header parsing in :class:`InertiaRequest`.
* Iteration ordering in ``build_props`` / ``build_merge_kinds`` when
  shared and per-request props are mixed.
* Default JSON encoder forwarding into :class:`InertiaResponse`.
* Request forwarding into Django's ``render_to_string``.
"""

from __future__ import annotations

from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings

from inertia.test import InertiaTestCase


class InertiaResponseHeadersTestCase(InertiaTestCase):
    """Mutations on the three canonical headers in ``InertiaResponse.__init__``.

    Kills ``__init__`` mutants that rewrite the literal header *names* with
    "XX" sentinels, the canonical *values* (``"X-Inertia"``, ``"true"``),
    and the entire ``headers=_headers`` forwarding (``mutmut_36`` / 17 / 20
    / 21 / 22 / 23 / 26 / 27).
    """

    def test_subsequent_inertia_response_emits_three_canonical_headers(self) -> None:
        response = self.inertia.get("/empty/")

        self.assertEqual(response.status_code, 200)
        # Django's middleware (e.g. SessionMiddleware) may append further
        # directives to ``Vary``, so split the header and compare directives
        # directly. Case-sensitive: ``Vary: x-inertia`` would be a wire-level
        # bug since the directive is the request header to vary on.
        vary_directives = [d.strip() for d in response.headers["Vary"].split(",")]
        self.assertIn("X-Inertia", vary_directives)
        self.assertEqual(response.headers["X-Inertia"], "true")
        self.assertEqual(response.headers["Content-Type"], "application/json")


class LocationHelperWireFormatTestCase(InertiaTestCase):
    """The 409 / ``X-Inertia-Location`` external-redirect signal.

    Kills the empty-body content mutation
    (``location__mutmut_14``: ``""`` → ``"XXXX"``) by asserting an exact
    empty body, and pins the canonical header name + value.
    """

    def test_external_redirect_returns_409_with_empty_body_and_location(self) -> None:
        response = self.client.get("/external-redirect/")

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.content, b"")
        self.assertEqual(response.headers["X-Inertia-Location"], "http://foobar.com/")


class InertiaRedirectHelperWireFormatTestCase(InertiaTestCase):
    """The 409 / ``X-Inertia-Redirect`` fragment-aware redirect signal.

    Kills ``inertia_redirect__mutmut_14`` (empty content → "XXXX") and pins
    the canonical header name + value forwarded from the helper's
    ``url`` argument.
    """

    def test_inertia_redirect_returns_409_with_empty_body_and_url(self) -> None:
        response = self.client.get("/inertia-redirect-helper/")

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.content, b"")
        self.assertEqual(response.headers["X-Inertia-Redirect"], "/foo#bar")


class FirstLoadInlineJSONEscapeTestCase(InertiaTestCase):
    """HTML-safe escaping applied before inline-JSON injection.

    The page-shell embeds the page JSON inside
    ``<script type="application/json">`` so an attacker-controlled prop
    value containing ``</script>``, ``<``, ``>``, or ``&`` must be
    escaped before it hits the wire. These assertions kill the
    ``build_first_load_context_and_template`` string mutations on each
    of the four ``data.replace(...)`` chains.
    """

    def test_special_chars_are_escaped_in_inline_page_json(self) -> None:
        response = self.client.get("/escape-chars/")
        body = response.content

        # Original prop value: "<script>alert(1)</script>&y". Each special
        # char must be escaped to its lowercase ``\uXXXX`` form. Pin the
        # following character too, so a mutation that wraps the
        # replacement value with junk (e.g. ``"XX>XX"``) is caught —
        # otherwise the escape sequence still appears as a substring.
        self.assertIn(b"\\u003cscript", body)
        self.assertIn(b"\\u003ealert", body)
        self.assertIn(b"\\u0026y", body)
        # Defensive: no unescaped occurrence of the prop value should
        # leak through. The ``<script type=\"application/json\">``
        # wrapper is the only literal ``<script`` in the document; the
        # mutation we kill would let ``<script>alert(1)`` through.
        self.assertNotIn(b"<script>alert(1)", body)
        self.assertNotIn(b"</script>&y", body)


class InertiaRequestHeaderSplitTestCase(InertiaTestCase):
    """Comma-splitting of multi-value Inertia request headers.

    Mutmut transforms ``header.split(",")`` into ``header.split(None)``
    (whitespace split — collapses ``"a,b"`` into ``["a,b"]``) and into
    ``header.split("XX,XX")`` (no comma at all). Two-value headers kill
    both shapes.
    """

    def test_partial_except_with_two_keys_excludes_both(self) -> None:
        self.inertia.get(
            "/partial-except/",
            HTTP_X_INERTIA_PARTIAL_DATA="name,sport,team,grit",
            HTTP_X_INERTIA_PARTIAL_EXCEPT="team,grit",
            HTTP_X_INERTIA_PARTIAL_COMPONENT="TestComponent",
        )
        page_props = self.props()
        self.assertIn("name", page_props)
        self.assertIn("sport", page_props)
        self.assertNotIn("team", page_props)
        self.assertNotIn("grit", page_props)

    def test_except_once_props_with_two_keys_omits_both(self) -> None:
        self.inertia.get(
            "/once-multiple/",
            HTTP_X_INERTIA_EXCEPT_ONCE_PROPS="plans,config",
        )
        page_props = self.props()
        self.assertNotIn("plans", page_props)
        self.assertNotIn("config", page_props)


class JsonEncoderForwardingTestCase(InertiaTestCase):
    """``json_encode(self.page_data(), cls=...)`` must use the configured encoder.

    Default :class:`json.JSONEncoder` cannot serialize :class:`datetime.date`,
    so a single ``date`` prop kills ``__init__`` mutants that drop
    ``cls`` (``mutmut_12`` / ``14``) or flip ``or`` → ``and``
    (``mutmut_15``, which yields ``None`` because the class attribute
    ``InertiaResponse.json_encoder`` is ``None``).
    """

    def test_inertia_response_uses_inertia_json_encoder_for_date_prop(self) -> None:
        response = self.inertia.get("/date-prop/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["props"]["when"], "2030-01-01")


class FirstLoadRequestForwardingTestCase(InertiaTestCase):
    """``build_first_load`` must forward ``self.request`` into ``render_to_string``.

    ``InertiaTestCase`` already wraps ``inertia.http.render_to_string`` with
    a mock; we just inspect ``call_args`` to assert the third positional
    arg is the live request. Kills ``build_first_load__mutmut_15``
    (``self.request`` → ``None``) and ``mutmut_18`` (line removed).
    """

    def test_render_to_string_receives_request_as_third_positional_arg(self) -> None:
        self.client.get("/empty/")

        self.assertIsNotNone(self.mock_render.call_args)
        positional_args = self.mock_render.call_args.args
        self.assertEqual(len(positional_args), 3)
        request_arg = positional_args[2]
        self.assertIsNotNone(request_arg)
        self.assertEqual(request_arg.path, "/empty/")


class MisconfiguredLayoutMessageTestCase(InertiaTestCase):
    """The full ``ImproperlyConfigured`` message is part of the public API.

    Tightens the existing partial substring assertion to the exact
    string. Kills ``build_first_load__mutmut_10`` which adds ``"XX"``
    sentinels around the message.
    """

    def test_misconfigured_layout_raises_with_exact_message(self) -> None:
        with (
            override_settings(INERTIA_LAYOUT=None),
            self.assertRaisesMessage(
                ImproperlyConfigured,
                "INERTIA_LAYOUT must be set in your Django settings",
            ),
        ):
            self.client.get("/props/")


class AlwaysIncludedKeyDoesNotShortCircuitLoopTestCase(InertiaTestCase):
    """``ALWAYS_INCLUDED_KEYS`` must ``continue`` (not ``break``) the prop loop.

    When ``share(request, errors=...)`` runs first, the resolved props
    dict iterates ``errors`` *before* per-request keys. ``mutmut_38``
    flips that ``continue`` to ``break``, which would skip every prop
    that follows and let ``IgnoreOnFirstLoadProp`` instances leak into
    the response on a non-partial render.
    """

    def test_optional_prop_after_shared_errors_is_dropped_on_first_load(
        self,
    ) -> None:
        self.inertia.get("/share-errors-then-optional/")
        page_props = self.props()

        self.assertIn("errors", page_props)
        self.assertNotIn("sport", page_props)


class MergeKindsContinuesPastNonMergingProp(InertiaTestCase):
    """``build_merge_kinds`` must ``continue`` past a non-merging Mergeable prop.

    A bare ``defer(...)`` is :class:`MergeableProp` but
    ``should_merge() == False``. Mutmut flips the ``continue`` after
    that check to ``break``, dropping every subsequent merging prop
    from the registry. A merge prop *after* the bare defer kills it.
    """

    def test_merge_prop_after_non_merging_defer_still_emits_merge_props(
        self,
    ) -> None:
        page = self.inertia.get("/merge-after-non-merging-defer/").json()

        self.assertEqual(page.get("mergeProps"), ["team"])


class OnceExceptOnPartialWithoutPartialDataTestCase(InertiaTestCase):
    """A partial render with ``X-Inertia-Except-Once-Props`` but no
    ``X-Inertia-Partial-Data`` must still drop the once-prop value.

    ``in_partial_data`` is the ``is_partial and key in partial_keys``
    short-circuit inside ``build_props``. When ``partial_keys`` is the
    empty list (no allow-list set), the ``and`` ensures
    ``in_partial_data`` is ``False`` and the standard
    "in-except-once and not fresh → drop" branch fires. ``mutmut_76``
    flips that to ``or``, which would preserve the value whenever
    ``is_partial`` is truthy — a wire-protocol divergence.
    """

    def test_once_prop_dropped_when_except_set_and_partial_data_unset(self) -> None:
        self.inertia.get(
            "/once/",
            HTTP_X_INERTIA_EXCEPT_ONCE_PROPS="plans",
            HTTP_X_INERTIA_PARTIAL_COMPONENT="TestComponent",
        )
        page_props = self.props()
        self.assertNotIn("plans", page_props)
        self.assertIn("name", page_props)


class RenderHelperPropsForwardingTestCase(InertiaTestCase):
    """``render(request, comp, props or {}, ...)`` must forward truthy ``props``.

    ``mutmut_9`` flips ``props or {}`` to ``props and {}``: when the
    caller passes a non-empty dict, the mutated form returns ``{}`` and
    the prop is silently dropped from the page object.
    """

    def test_render_with_explicit_props_keeps_those_props(self) -> None:
        page = self.inertia.get("/render-helper-with-props/").json()

        self.assertEqual(page["props"].get("hello"), "world")
