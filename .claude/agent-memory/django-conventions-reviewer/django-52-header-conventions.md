---
name: django-52-header-conventions
description: Confirmed Django stable/5.2.x conventions for response-header writes, middleware mutation, empty values, test-client headers, build_absolute_uri (verified 2026-07-16)
metadata:
  type: reference
---

Confirmed conventions on django/django branch `stable/5.2.x` (fetched 2026-07-16; response.py last commit 2026-06-03):

- `django/middleware/clickjacking.py:L25-L38` — core middleware writes headers as `response.headers["X-Frame-Options"] = ...`; legacy read `response.get(...)` in the same method.
- `django/middleware/security.py:L33-L66` — mixes `response.headers[...] = ...` (L44), `response.headers.setdefault(...)` (L47, L52) and legacy `response.setdefault(...)` (L62) plus `"X" not in response` (L37). Both spellings are current core style; `=` when the middleware owns the header, `setdefault` when deferring to upstream.
- `django/http/response.py:L197-L198` — `HttpResponseBase.__setitem__` just delegates to `self.headers[header] = value`; the two write spellings are one code path. Neither deprecated.
- `django/views/static.py:L60-L64` — build response, then assign `response.headers[...]`, then return: core's build-then-set shape inside one function.
- `django/http/response.py:L90-L93` (`ResponseHeaders.__setitem__`) + `L48-L85` (`_convert_to_charset`) — `BadHeaderError` ONLY for `\r`/`\n`; empty string `""` passes; non-str is silently coerced via `str(value)` (L61-62; `None` → `"None"`).
- `django/http/response.py:L178-L185` — `serialize_headers` emits empty values as `X-Foo: `; `django/core/handlers/wsgi.py:L128-L133` passes `("X-Foo", "")` verbatim to `start_response`. No core first-party site sets an intentionally empty header, but behavior is fully defined; membership (`__contains__`/`has_header`, L206-L210) is presence-based, not truthiness-based.
- `django/http/response.py:L117-L120` — constructor `headers=` kwarg (3.2+) is the other idiomatic way to attach headers at build time.
- `django/test/client.py:L633-L663` — `RequestFactory.generic(..., *, headers=None, query_params=None, **extra)`; `headers=` merges into the same WSGI `extra` dict via `HttpHeaders.to_wsgi_names` (L662-663). Legacy `HTTP_*` kwargs are the same mechanism, still fully supported.
- `docs/topics/testing/tools.txt:L141-L144` (5.2) — "Keyword arguments starting with a ``HTTP_`` prefix are set as headers, but the ``headers`` parameter should be preferred for readability." Preference, not deprecation. `headers=` added in 4.2 (docs/releases/4.2.txt).
- `tests/middleware/test_security.py:L45-L54` — core test idiom: `@override_settings(...)` per method + `assertEqual(response.headers["Strict-Transport-Security"], ...)`; presence via `assertIn(..., response.headers)`.
- `tests/httpwrappers/tests.py:L992-L1023` (`HttpResponseHeadersTestCase`) — core tests assert BOTH `response["X-Foo"]` and `response.headers["X-Foo"]`.
- `django/contrib/auth/decorators.py:L22-L23` — `path = request.build_absolute_uri()` is core's idiom for "absolute URL of the request being processed".

See [[deprecation-watch]] and [[house-style-test-client-kwargs]].
